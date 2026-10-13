"""Tests for poll and voice-message handling in server.py.

Needs the app's own dependencies (Flask etc.); the whole module is skipped
if they are missing. Run from the repository root:

    python -m unittest discover -s tests -v
"""
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

_SCRATCH = tempfile.mkdtemp(prefix="family-chat-tests-")
os.environ.setdefault("FAMILY_CHAT_DATA_DIR", _SCRATCH)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "family-chat" / "app"))

try:
    import server  # noqa: E402
except ImportError:  # pragma: no cover - depends on the environment
    server = None


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class ValidatePollTests(unittest.TestCase):
    def poll(self, **overrides):
        data = {"question": "Pizza or tacos?", "options": ["Pizza", "Tacos"]}
        data.update(overrides)
        return server.validate_poll(data)

    def test_valid_poll_is_trimmed_and_single_choice_by_default(self):
        poll, error = self.poll(question="  Pizza or tacos?  ", options=["  Pizza ", "Tacos"])
        self.assertIsNone(error)
        self.assertEqual(poll, {"question": "Pizza or tacos?", "options": ["Pizza", "Tacos"], "multiple": False})

    def test_multiple_must_be_a_real_boolean(self):
        self.assertTrue(self.poll(multiple=True)[0]["multiple"])
        self.assertFalse(self.poll(multiple="true")[0]["multiple"])
        self.assertFalse(self.poll(multiple=1)[0]["multiple"])

    def test_duplicate_blank_and_non_string_options_are_dropped(self):
        poll, error = self.poll(options=["Pizza", " pizza", "", "   ", None, 5, {"x": 1}, "Tacos"])
        self.assertIsNone(error)
        self.assertEqual(poll["options"], ["Pizza", "Tacos"])

    def test_rejections(self):
        cases = [
            ({"question": ""}, "question"),
            ({"question": ["q"]}, "question"),
            ({"question": "q" * 301}, "300"),
            ({"options": ["only one"]}, "two different"),
            ({"options": ["same", "SAME"]}, "two different"),
            ({"options": "not a list"}, "two different"),
            ({"options": [str(i) for i in range(11)]}, "at most 10"),
            ({"options": ["ok", "x" * 101]}, "100"),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                poll, error = self.poll(**overrides)
                self.assertIsNone(poll)
                self.assertIn(expected, error)


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class PollVotingTests(unittest.TestCase):
    """Drives the real socket handlers through Flask-SocketIO's test client."""

    @classmethod
    def setUpClass(cls):
        server.init_db()

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def client(self, user_id, name):
        c = server.socketio.test_client(server.app, headers={"X-Remote-User-Id": user_id, "X-Remote-User-Name": name})
        c.emit("join", {"room": "general"})
        c.get_received()
        return c

    def create_poll(self, client, multiple=False):
        client.emit("create_poll", {"channel": "general", "question": "When?", "options": ["Sat", "Sun", "Mon"], "multiple": multiple})
        new = [e for e in client.get_received() if e["name"] == "new_message"]
        self.assertEqual(len(new), 1)
        return new[0]["args"][0]["id"]

    def vote(self, client, message_id, option_index):
        client.emit("poll_vote", {"message_id": message_id, "option_index": option_index})
        updates = [e for e in client.get_received() if e["name"] == "poll_updated"]
        if not updates:
            return None
        votes = updates[-1]["args"][0]["votes"]
        return {int(k): sorted(v["id"] for v in voters) for k, voters in votes.items()}

    def test_single_choice_vote_moves_and_toggles_off(self):
        alice, bob = self.client("alice", "Alice"), self.client("bob", "Bob")
        pid = self.create_poll(alice)
        bob.get_received()
        self.assertEqual(self.vote(alice, pid, 0), {0: ["alice"]})
        self.assertEqual(self.vote(alice, pid, 2), {2: ["alice"]})
        self.assertEqual(self.vote(bob, pid, 2), {2: ["alice", "bob"]})
        self.assertEqual(self.vote(alice, pid, 2), {2: ["bob"]})

    def test_multiple_choice_keeps_every_pick(self):
        alice = self.client("alice", "Alice")
        pid = self.create_poll(alice, multiple=True)
        self.vote(alice, pid, 0)
        self.assertEqual(self.vote(alice, pid, 1), {0: ["alice"], 1: ["alice"]})
        self.assertEqual(self.vote(alice, pid, 0), {1: ["alice"]})

    def test_invalid_votes_are_ignored(self):
        alice = self.client("alice", "Alice")
        pid = self.create_poll(alice)
        self.assertIsNone(self.vote(alice, pid, 3))
        self.assertIsNone(self.vote(alice, pid, -1))
        self.assertIsNone(self.vote(alice, pid, "x"))
        alice.emit("send_message", {"channel": "general", "content": "just text"})
        text_id = [e for e in alice.get_received() if e["name"] == "new_message"][0]["args"][0]["id"]
        self.assertIsNone(self.vote(alice, text_id, 0))

    def test_votes_are_loaded_with_history_and_removed_with_the_poll(self):
        alice = self.client("alice", "Alice")
        pid = self.create_poll(alice)
        self.vote(alice, pid, 1)
        loaded = next(m for m in server.get_messages(channel="general") if m["id"] == pid)
        self.assertEqual([v["id"] for v in loaded["poll_votes"][1]], ["alice"])
        alice.emit("delete_message", {"message_id": pid})
        alice.get_received()
        conn = server.sqlite3.connect(server.DB_PATH)
        remaining = conn.execute("SELECT COUNT(*) FROM poll_votes WHERE message_id = ?", (pid,)).fetchone()[0]
        conn.close()
        self.assertEqual(remaining, 0)


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class VoiceAndSummaryTests(unittest.TestCase):
    def test_voice_messages_need_an_audio_file(self):
        self.assertEqual(server.validate_outgoing_file("voice", None), "Invalid voice message.")
        self.assertEqual(server.validate_outgoing_file("voice", {"url": "/uploads/x.png", "mime_type": "image/png"}),
                         "Invalid voice message.")
        self.assertIn("wasn't found", server.validate_outgoing_file(
            "voice", {"url": "https://example.com/x.webm", "mime_type": "audio/webm"}))

    def test_summaries(self):
        self.assertEqual(server.summarize_message_for_notification('{"question": "When?"}', "poll", None), "📊 Poll: When?")
        self.assertEqual(server.summarize_message_for_notification("not json", "poll", None), "Started a poll")
        self.assertEqual(server.summarize_message_for_notification("", "voice", None), "Sent a voice message")

    def test_link_preview_url_drops_surrounding_bold_markers(self):
        self.assertEqual(server.extract_single_url("**https://example.com/a_b**"), "https://example.com/a_b")


if __name__ == "__main__":
    unittest.main()
