"""Tests for profile details (birthdate, anniversary, phone) and the
profile card's Home Assistant person lookup.

Needs the app's own dependencies (Flask etc.); skipped if they are missing.
Run from the repository root:

    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault("FAMILY_CHAT_DATA_DIR", tempfile.mkdtemp(prefix="family-chat-tests-"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "family-chat" / "app"))

try:
    import server  # noqa: E402
except ImportError:  # pragma: no cover - depends on the environment
    server = None


def headers(user_id, name="Someone"):
    return {"X-Remote-User-Id": user_id, "X-Remote-User-Name": name}


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class ValidateProfileTests(unittest.TestCase):
    def check(self, **fields):
        return server.validate_profile_details(fields)

    def test_valid_values_are_trimmed(self):
        details, error = self.check(birthdate=" 1985-03-04 ", anniversary="2010-06-12", phone=" +1 (415) 555-2671 ")
        self.assertIsNone(error)
        self.assertEqual(details, {"birthdate": "1985-03-04", "anniversary": "2010-06-12", "phone": "+1 (415) 555-2671"})

    def test_everything_may_be_left_empty(self):
        self.assertEqual(self.check(), ({"birthdate": "", "anniversary": "", "phone": ""}, None))
        self.assertEqual(self.check(birthdate=None)[1], None)

    def test_bad_dates_are_rejected(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        for value in ("1985-02-30", "03/04/1985", "1899-12-31", tomorrow, "not a date"):
            with self.subTest(value=value):
                self.assertIsNotNone(self.check(birthdate=value)[1])
                self.assertIsNotNone(self.check(anniversary=value)[1])

    def test_bad_phone_numbers_are_rejected(self):
        for value in ("12", "call me", "555-1234<script>", "+" + "1" * 21, "1" * 31, "555--1234 ext. 9", "-5551234"):
            with self.subTest(value=value):
                self.assertIsNotNone(self.check(phone=value)[1])

    def test_non_text_values_are_rejected(self):
        self.assertIsNotNone(self.check(phone=5551234567)[1])
        self.assertIsNotNone(self.check(birthdate=["1985-03-04"])[1])


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class ProfileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.init_db()
        server.record_ha_user("alice", "alice", "Alice")
        server.record_ha_user("bob", "bob", "Bob")

    def setUp(self):
        self.client = server.app.test_client()
        server._person_entities_cache.update(fetched_at=None, by_user={})
        self.addCleanup(server.set_profile_details, "alice", dict.fromkeys(server.PROFILE_FIELDS, ""))

    def test_saving_and_reading_your_own_details(self):
        resp = self.client.post("/api/my-profile", headers=headers("alice"),
                                json={"birthdate": "1985-03-04", "anniversary": "", "phone": "555-123-4567"})
        self.assertEqual(resp.status_code, 200, resp.get_json())
        me = self.client.get("/api/me", headers=headers("alice")).get_json()
        self.assertEqual((me["birthdate"], me["anniversary"], me["phone"]), ("1985-03-04", "", "555-123-4567"))

    def test_saving_only_ever_changes_your_own_profile(self):
        self.client.post("/api/my-profile", headers=headers("alice"),
                         json={"phone": "555-123-4567", "user_id": "bob"})
        self.assertEqual(server.get_profile_details("bob")["phone"], "")
        self.assertEqual(server.get_profile_details("alice")["phone"], "555-123-4567")

    def test_invalid_details_are_refused_and_nothing_changes(self):
        server.set_profile_details("alice", {"birthdate": "1985-03-04", "anniversary": "", "phone": ""})
        resp = self.client.post("/api/my-profile", headers=headers("alice"), json={"birthdate": "1985-13-01"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(server.get_profile_details("alice")["birthdate"], "1985-03-04")

    def test_clearing_everything_removes_the_row(self):
        server.set_profile_details("alice", {"birthdate": "1985-03-04", "anniversary": "", "phone": ""})
        self.client.post("/api/my-profile", headers=headers("alice"), json={})
        conn = server.sqlite3.connect(server.DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM user_profiles WHERE user_id = 'alice'").fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)

    def test_profile_card_shows_someone_elses_details(self):
        server.set_profile_details("alice", {"birthdate": "1985-03-04", "anniversary": "2010-06-12", "phone": "555-123-4567"})
        with mock.patch.object(server, "ha_api_request", return_value=(None, "unavailable")):
            card = self.client.get("/api/profile/alice", headers=headers("bob")).get_json()
        self.assertEqual(card["name"], "Alice")
        self.assertEqual((card["birthdate"], card["anniversary"], card["phone"]), ("1985-03-04", "2010-06-12", "555-123-4567"))
        self.assertIsNone(card["person_entity"])

    def test_profile_card_needs_home_assistant_and_a_known_person(self):
        self.assertEqual(self.client.get("/api/profile/alice").status_code, 403)
        self.assertEqual(self.client.get("/api/profile/nobody", headers=headers("bob")).status_code, 404)

    def test_person_entity_must_be_linked_and_locatable(self):
        states = [
            {"entity_id": "person.alice", "attributes": {"user_id": "alice", "device_trackers": ["device_tracker.alice_phone"]}},
            {"entity_id": "person.bob", "attributes": {"user_id": "bob", "device_trackers": []}},
            {"entity_id": "person.carol", "attributes": {"user_id": "carol", "latitude": 52.1, "longitude": 4.3}},
            {"entity_id": "sensor.alice", "attributes": {"user_id": "alice", "device_trackers": ["x"]}},
        ]
        with mock.patch.object(server, "ha_api_request", return_value=(states, None)) as request:
            self.assertEqual(server.find_person_entity("alice"), "person.alice")
            self.assertIsNone(server.find_person_entity("bob"))  # linked, but nothing to locate them with
            self.assertEqual(server.find_person_entity("carol"), "person.carol")
            self.assertIsNone(server.find_person_entity("dave"))
            self.assertEqual(request.call_count, 1)  # cached between cards


if __name__ == "__main__":
    unittest.main()
