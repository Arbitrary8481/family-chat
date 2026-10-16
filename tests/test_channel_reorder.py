"""Tests for drag-and-drop channel reordering (POST /api/channels/reorder),
used by both the admin panel and the chat's Settings → Channels tab.

Needs the app's own dependencies (Flask etc.); skipped if they are missing.
Run from the repository root:

    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("FAMILY_CHAT_DATA_DIR", tempfile.mkdtemp(prefix="family-chat-tests-"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "family-chat" / "app"))

try:
    import server  # noqa: E402
except ImportError:  # pragma: no cover - depends on the environment
    server = None


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class ChannelReorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.init_db()
        # A fresh database has a single category; a second one is needed
        # to drag a channel between categories.
        if len(server.get_categories()) < 2:
            server.add_category("Reorder test")

    def setUp(self):
        self.addCleanup(server.set_setting, "owner_user_id", server.get_setting("owner_user_id") or "")
        server.set_setting("owner_user_id", "owner_id")
        self.original = self.order()
        self.addCleanup(self.restore)

    def order(self):
        result = {}
        for ch in server.get_channels():
            result.setdefault(str(ch["category_id"]), []).append(ch["slug"])
        for cat in server.get_categories():
            result.setdefault(str(cat["id"]), [])
        return result

    def restore(self):
        ok, error = server.reorder_channels(self.original)
        self.assertTrue(ok, error)

    def post(self, user_id, channels, admin=False):
        client = server.app.test_client()
        if admin:
            with client.session_transaction() as sess:
                sess["is_admin"] = True
        return client.post("/api/channels/reorder", json={"channels": channels},
                           headers={"X-Remote-User-Id": user_id, "X-Remote-User-Name": "Someone"})

    def moved_last_channel_to_first_category(self):
        order = {k: list(v) for k, v in self.original.items()}
        categories = [str(c["id"]) for c in server.get_categories()]
        source = next(c for c in categories if order[c])
        slug = order[source].pop()
        target = next(c for c in categories if c != source)
        order[target].insert(0, slug)
        return order, slug, target

    def test_owner_can_move_a_channel_into_another_category(self):
        order, slug, first_category = self.moved_last_channel_to_first_category()
        resp = self.post("owner_id", order)
        self.assertEqual(resp.status_code, 200, resp.get_json())
        channels = resp.get_json()["channels"]
        moved = next(ch for ch in channels if ch["slug"] == slug)
        self.assertEqual(str(moved["category_id"]), first_category)
        self.assertEqual(self.order(), order)

    def test_admin_session_can_reorder(self):
        order, _, _ = self.moved_last_channel_to_first_category()
        resp = self.post("someone_else", order, admin=True)
        self.assertEqual(resp.status_code, 200, resp.get_json())

    def test_other_people_cannot_reorder(self):
        order, _, _ = self.moved_last_channel_to_first_category()
        resp = self.post("someone_else", order)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.order(), self.original)

    def test_a_channel_listed_twice_is_rejected(self):
        source = next(c for c in self.original if self.original[c])
        slug = self.original[source][0]
        other = next(c for c in self.original if c != source)
        twice_in_one = {**self.original, source: self.original[source] + [slug]}
        in_two = {**self.original, other: self.original[other] + [slug]}
        for bad in (twice_in_one, in_two):
            with self.subTest(bad=bad):
                self.assertEqual(self.post("owner_id", bad).status_code, 400)
        self.assertEqual(self.order(), self.original)

    def test_stale_or_unknown_channels_are_rejected(self):
        order = {k: list(v) for k, v in self.original.items()}
        first = next(c for c in order if order[c])
        dropped = {**order, first: order[first][1:]}
        unknown = {**order, first: order[first] + ["not-a-channel"]}
        for bad in (dropped, unknown, {"999999": []}, "not a dict"):
            with self.subTest(bad=bad):
                self.assertEqual(self.post("owner_id", bad).status_code, 400)
        self.assertEqual(self.order(), self.original)


if __name__ == "__main__":
    unittest.main()
