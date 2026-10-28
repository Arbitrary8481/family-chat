"""Tests for calendar display names: Home Assistant 2026.11's
"<device> <entity>" naming on 2026.11 and later, friendly_name before.

Needs the app's own dependencies (Flask etc.); skipped if they are missing.
Run from the repository root:

    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("FAMILY_CHAT_DATA_DIR", tempfile.mkdtemp(prefix="family-chat-tests-"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "family-chat" / "app"))

try:
    import server  # noqa: E402
except ImportError:  # pragma: no cover - depends on the environment
    server = None

STATES = [
    {"entity_id": "calendar.family", "attributes": {"friendly_name": "Family"}},
    {"entity_id": "calendar.power_meter_off_peak", "attributes": {"friendly_name": "Off-peak"}},
    {"entity_id": "calendar.kitchen", "attributes": {"friendly_name": "Kitchen display Calendar"}},
    {"entity_id": "light.porch", "attributes": {"friendly_name": "Porch"}},
]


NEW_NAMES = [
    {"entity_id": "calendar.family", "entity": "Family", "device": None},
    {"entity_id": "calendar.power_meter_off_peak", "entity": "Off-peak", "device": "Power meter"},
    {"entity_id": "calendar.kitchen", "entity": None, "device": "Kitchen display"},
]

OLD_NAMES = {
    "calendar.family": "Family",
    "calendar.power_meter_off_peak": "Off-peak",
    "calendar.kitchen": "Kitchen display Calendar",
}


def fake_api(template_result, version="2026.11.0", calls=None):
    """ha_api_request stand-in: /states always works; /config reports
    version (or fails if it is None); /template returns template_result,
    or fails if it is None."""
    def request(method, path, json_body=None, timeout=5):
        if calls is not None:
            calls.append(path)
        if path == "/states":
            return STATES, None
        if path == "/config":
            return ({"version": version}, None) if version else (None, "Could not reach Home Assistant.")
        if path == "/template":
            if template_result is None:
                return None, "Home Assistant returned an error for that request."
            return template_result, None
        raise AssertionError(f"unexpected call {method} {path}")
    return request


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class ComposeNameTests(unittest.TestCase):
    def test_device_then_entity(self):
        self.assertEqual(server.compose_entity_display_name("Off-peak", "Power meter"), "Power meter Off-peak")

    def test_entity_without_device(self):
        self.assertEqual(server.compose_entity_display_name("Family", None), "Family")

    def test_main_entity_uses_device_name(self):
        self.assertEqual(server.compose_entity_display_name(None, "Kitchen display"), "Kitchen display")
        self.assertEqual(server.compose_entity_display_name("", "Kitchen display"), "Kitchen display")

    def test_no_duplicate_device_prefix(self):
        self.assertEqual(server.compose_entity_display_name("Power meter Off-peak", "Power meter"), "Power meter Off-peak")
        self.assertEqual(server.compose_entity_display_name("Power meter", "Power meter"), "Power meter")

    def test_nothing_to_go_on(self):
        self.assertIsNone(server.compose_entity_display_name(None, None))


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class CalendarNameTests(unittest.TestCase):
    def setUp(self):
        for attr in ("_calendar_names_failed_at", "_ha_version_cache"):
            setattr(server, attr, None)
            self.addCleanup(setattr, server, attr, None)

    def names(self, template_result, version="2026.11.0", calls=None):
        server._ha_version_cache = None
        api = fake_api(template_result, version, calls)
        with mock.patch.object(server, "ha_api_request", side_effect=api):
            calendars, error = server.get_calendar_entities()
        self.assertIsNone(error)
        return {c["entity_id"]: c["name"] for c in calendars}

    def test_new_naming_on_2026_11_and_later(self):
        expected = {
            "calendar.family": "Family",
            "calendar.power_meter_off_peak": "Power meter Off-peak",
            "calendar.kitchen": "Kitchen display",
        }
        for version in ("2026.11.0", "2026.11.0b3", "2026.12.1", "2027.1.0"):
            with self.subTest(version=version):
                self.assertEqual(self.names(NEW_NAMES, version), expected)

    def test_earlier_versions_keep_friendly_name_and_skip_the_template(self):
        for version in ("2026.10.3", "2026.4.0", "2025.12.0"):
            with self.subTest(version=version):
                calls = []
                self.assertEqual(self.names(NEW_NAMES, version, calls), OLD_NAMES)
                self.assertNotIn("/template", calls)

    def test_unknown_version_keeps_friendly_name(self):
        calls = []
        self.assertEqual(self.names(NEW_NAMES, None, calls), OLD_NAMES)
        self.assertNotIn("/template", calls)

    def test_failed_render_keeps_friendly_name(self):
        self.assertEqual(self.names(None), OLD_NAMES)

    def test_upgrade_is_noticed_without_a_restart(self):
        with mock.patch.object(server, "ha_api_request", side_effect=fake_api(NEW_NAMES, "2026.10.3")):
            self.assertEqual(server.get_ha_version(), (2026, 10))
        with mock.patch.object(server.time, "monotonic", return_value=time.monotonic() + server.HA_VERSION_TTL_SECONDS + 1), \
                mock.patch.object(server, "ha_api_request", side_effect=fake_api(NEW_NAMES, "2026.11.0")):
            self.assertEqual(server.get_ha_version(), (2026, 11))

    def test_missing_or_odd_entries_fall_back(self):
        names = self.names([{"entity_id": "calendar.family", "entity": None, "device": None}, "junk"])
        self.assertEqual(names["calendar.family"], "Family")
        self.assertEqual(names["calendar.kitchen"], "Kitchen display Calendar")

    def test_failure_is_not_retried_every_time(self):
        calls = []
        with mock.patch.object(server, "ha_api_request", side_effect=fake_api(None, calls=calls)):
            server.get_calendar_entities()
            server.get_calendar_entities()
        self.assertEqual(calls.count("/template"), 1)

    def test_template_uses_new_functions(self):
        self.assertIn("entity_name(", server.CALENDAR_NAMES_TEMPLATE)
        self.assertIn("device_name(", server.CALENDAR_NAMES_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
