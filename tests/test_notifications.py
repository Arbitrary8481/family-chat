"""Tests for where a tapped notification sends you (server.notification_link)
and the payload sent to the Companion App.

Needs the app's own dependencies (Flask etc.); skipped if they are missing.
Run from the repository root:

    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("FAMILY_CHAT_DATA_DIR", tempfile.mkdtemp(prefix="family-chat-tests-"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "family-chat" / "app"))

try:
    import server  # noqa: E402
except ImportError:  # pragma: no cover - depends on the environment
    server = None


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class NotificationLinkTests(unittest.TestCase):
    def setUp(self):
        server._uses_app_panel_cache = None
        self.addCleanup(setattr, server, "_uses_app_panel_cache", None)
        patcher = mock.patch.object(server, "get_own_slug", return_value="c2f85679_family_chat")
        patcher.start()
        self.addCleanup(patcher.stop)

    def link(self, version, channel="random"):
        server._uses_app_panel_cache = None
        config = ({"version": version}, None) if version else (None, "unreachable")
        with mock.patch.object(server, "ha_api_request", return_value=config):
            return server.notification_link(channel)

    def test_current_home_assistant_opens_the_channel_inside_the_app_panel(self):
        self.assertEqual(self.link("2026.10.1"), "/app/c2f85679_family_chat/channel/random")
        self.assertEqual(self.link("2026.2.0"), "/app/c2f85679_family_chat/channel/random")
        self.assertEqual(self.link("2027.1.0b2"), "/app/c2f85679_family_chat/channel/random")

    def test_no_channel_opens_the_app(self):
        self.assertEqual(self.link("2026.10.1", channel=None), "/app/c2f85679_family_chat")

    def test_before_2026_2_the_old_ingress_page_is_used(self):
        self.assertEqual(self.link("2026.1.3"), "/hassio/ingress/c2f85679_family_chat")
        self.assertEqual(self.link("2025.12.0"), "/hassio/ingress/c2f85679_family_chat")

    def test_unknown_version_assumes_the_current_layout(self):
        self.assertEqual(self.link(None), "/app/c2f85679_family_chat/channel/random")

    def test_no_link_without_the_apps_slug(self):
        with mock.patch.object(server, "get_own_slug", return_value=None):
            self.assertIsNone(server.notification_link("random"))

    def test_payload_sets_the_link_for_android_and_ios(self):
        calls = []

        def fake_request(method, path, json_body=None, timeout=5):
            calls.append((method, path, json_body))
            return ({"version": "2026.10.1"}, None) if path == "/config" else ({}, None)

        with mock.patch.object(server, "ha_api_request", side_effect=fake_request):
            ok, error = server.send_ha_notification("mobile_app_pixel", "Bob in #random", "hi", channel="random")
        self.assertTrue(ok, error)
        method, path, body = calls[-1]
        self.assertEqual((method, path), ("POST", "/services/notify/mobile_app_pixel"))
        link = "/app/c2f85679_family_chat/channel/random"
        self.assertEqual(body["data"], {"clickAction": link, "url": link})


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class StripFormattingTests(unittest.TestCase):
    def test_marks_are_removed_like_the_chat_hides_them(self):
        cases = [
            ("Trip on **Saturday**, _bring snacks_:\n- `sunscreen`\n- towels",
             "Trip on Saturday, bring snacks:\n• sunscreen\n• towels"),
            ("3. leave at 9\n4. lunch at **noon**", "3. leave at 9\n4. lunch at noon"),
            ("look:\n```\ngate **code**\n```\nthanks", "look:\ngate **code**\nthanks"),
            ("snake_case, 5*3*2 and :smug_face: stay", "snake_case, 5*3*2 and :smug_face: stay"),
            ("**https://example.com/a_b_c**", "https://example.com/a_b_c"),
            ("`code with **stars**` then **bold**", "code with **stars** then bold"),
            ("** not bold **", "** not bold **"),
            ("", ""),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(server.strip_formatting(text), expected)

    def test_summaries_are_stripped_before_truncating(self):
        # 203 characters raw, 199 without the marks: fits, so nothing is cut.
        summary = server.summarize_message_for_notification("**" + "a" * 199 + "**", "text", None)
        self.assertEqual(summary, "a" * 199)
        self.assertEqual(server.summarize_message_for_notification("_hi_ **there**", "text", None), "hi there")

    def test_notification_body_has_no_marks(self):
        sent = []
        with mock.patch.object(server, "SUPERVISOR_TOKEN", "token"), \
             mock.patch.object(server, "get_subscribers_for_channel", return_value=[("bob", "mobile_app_pixel")]), \
             mock.patch.object(server, "get_notify_service", return_value=None), \
             mock.patch.object(server, "send_ha_notification", side_effect=lambda *a, **k: sent.append(a) or (True, None)):
            server.notify_message_subscribers("general", "Alice", "alice", "Dinner at **6**, bring `forks`", "text", None)
        self.assertEqual(sent[0][2], "Dinner at 6, bring forks")

    def test_activity_log_entries_saved_with_marks_are_shown_without_them(self):
        server.init_db()
        server.record_moderation_action("delete", 1, "Alice", "alice", "general", "**old** raw _summary_",
                                        "alice", "Alice", "self")
        self.assertEqual(server.get_moderation_log(limit=1)[0]["message_summary"], "old raw summary")


if __name__ == "__main__":
    unittest.main()
