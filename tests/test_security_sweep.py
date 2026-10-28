"""Tests for the fixes from the October 2026 security sweep.

Needs the app's own dependencies (Flask etc.); skipped if they are missing.
Run from the repository root:

    python -m unittest discover -s tests -v
"""
import os
import sqlite3
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

HEADERS = {"X-Remote-User-Id": "user-a", "X-Remote-User-Name": "alice"}


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class IngressOnlyTests(unittest.TestCase):
    def get(self, remote_addr, path="/api/channels"):
        client = server.app.test_client()
        return client.get(path, headers=HEADERS, environ_base={"REMOTE_ADDR": remote_addr})

    def test_ingress_proxy_is_allowed(self):
        self.assertEqual(self.get("172.30.32.2").status_code, 200)

    def test_loopback_is_allowed(self):
        self.assertEqual(self.get("127.0.0.1").status_code, 200)
        self.assertEqual(self.get("::1").status_code, 200)
        self.assertEqual(self.get("::ffff:172.30.32.2").status_code, 200)

    def test_other_containers_are_refused(self):
        for addr in ("172.30.33.5", "172.30.32.1", "192.168.1.20", "", "not-an-ip"):
            with self.subTest(addr=addr):
                response = self.get(addr)
                self.assertEqual(response.status_code, 403)
                self.assertIn(b"only accepts connections through Home Assistant", response.data)

    def test_socketio_is_covered_too(self):
        response = self.get("172.30.33.5", "/socket.io/?EIO=4&transport=polling")
        self.assertEqual(response.status_code, 403)


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class SharedFileTests(unittest.TestCase):
    def make_upload(self, name):
        path = server.UPLOAD_FOLDER / name
        path.write_bytes(b"data")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path, f"/uploads/{name}"

    def add_message(self, file_url, sender_id):
        msg_id = server.save_message("Someone", "", "general", "image", file_url, "x.png", 4,
                                     "image/png", sender_id=sender_id)
        self.addCleanup(self.drop_message, msg_id)
        return msg_id

    def drop_message(self, msg_id):
        conn = sqlite3.connect(server.DB_PATH)
        conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()

    def test_deleting_a_copy_keeps_the_original_file(self):
        path, url = self.make_upload("shared_photo.png")
        self.add_message(url, "victim")
        copy_id = self.add_message(url, "attacker")
        channel, error = server.delete_message(copy_id, "attacker", False, "Attacker", None)
        self.assertIsNone(error)
        self.assertTrue(path.exists())

    def test_a_file_used_as_an_avatar_is_kept(self):
        path, url = self.make_upload("avatar_victim_1.png")
        server.set_avatar("victim-avatar", url)
        self.addCleanup(server.delete_avatar, "victim-avatar")
        copy_id = self.add_message(url, "attacker")
        server.delete_message(copy_id, "attacker", False, "Attacker", None)
        self.assertTrue(path.exists())

    def test_the_last_use_still_removes_the_file(self):
        path, url = self.make_upload("only_photo.png")
        msg_id = self.add_message(url, "owner")
        server.delete_message(msg_id, "owner", False, "Owner", None)
        self.assertFalse(path.exists())

    def test_same_second_uploads_get_different_names(self):
        stem = "image_1700000000"
        first = server.unique_upload_path(stem, ".png")
        second = server.unique_upload_path(stem, ".png")
        self.addCleanup(first.unlink, missing_ok=True)
        self.addCleanup(second.unlink, missing_ok=True)
        self.assertEqual(first.name, "image_1700000000.png")
        self.assertEqual(second.name, "image_1700000000_1.png")


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class AdminPasswordTests(unittest.TestCase):
    def setUp(self):
        server._admin_login_failures.clear()

    def login(self, client, password):
        return client.post("/admin/login", data={"password": password}, headers=HEADERS)

    def is_admin(self, client):
        with client.session_transaction() as sess:
            with server.app.test_request_context():
                server.session.update(sess)
                return server.is_admin_session()

    def test_default_password_cannot_log_in(self):
        for password in ("changeme", "", "  "):
            with self.subTest(password=password), \
                    mock.patch.object(server, "ADMIN_PASSWORD", password), \
                    mock.patch.object(server, "ADMIN_PASSWORD_UNSET", True):
                client = server.app.test_client()
                self.login(client, password)
                self.assertFalse(self.is_admin(client))
                page = client.get("/admin", headers=HEADERS)
                self.assertIn(b"Admin login is turned off", page.data)

    def test_real_password_logs_in(self):
        with mock.patch.object(server, "ADMIN_PASSWORD", "s3cret-pass"), \
                mock.patch.object(server, "ADMIN_PASSWORD_HASH", server.generate_password_hash("s3cret-pass")), \
                mock.patch.object(server, "ADMIN_PASSWORD_UNSET", False):
            client = server.app.test_client()
            self.login(client, "s3cret-pass")
            self.assertTrue(self.is_admin(client))

    def test_a_restart_ends_admin_sessions(self):
        # Changing the password only takes effect after a restart, which
        # picks a new session token.
        with mock.patch.object(server, "ADMIN_PASSWORD", "old-pass"), \
                mock.patch.object(server, "ADMIN_PASSWORD_HASH", server.generate_password_hash("old-pass")), \
                mock.patch.object(server, "ADMIN_PASSWORD_UNSET", False):
            client = server.app.test_client()
            self.login(client, "old-pass")
            self.assertTrue(self.is_admin(client))
            with mock.patch.object(server, "_ADMIN_SESSION_TOKEN", "token-after-restart"):
                self.assertFalse(self.is_admin(client))

    def test_session_key_is_not_derived_from_the_password(self):
        with mock.patch.object(server, "ADMIN_PASSWORD", "one"):
            first = server._admin_session_key()
        with mock.patch.object(server, "ADMIN_PASSWORD", "two"):
            self.assertEqual(server._admin_session_key(), first)

    def test_old_style_session_without_key_is_not_admin(self):
        with mock.patch.object(server, "ADMIN_PASSWORD_UNSET", False):
            client = server.app.test_client()
            with client.session_transaction() as sess:
                sess["is_admin"] = True
            self.assertFalse(self.is_admin(client))


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class GifAndReactionTests(unittest.TestCase):
    def test_only_giphy_addresses_are_gifs(self):
        good = ["https://media2.giphy.com/media/abc/giphy.gif", "https://i.giphy.com/abc.gif",
                "https://giphy.com/x.gif"]
        bad = ["http://media2.giphy.com/a.gif", "https://evil.example/giphy.com/a.gif",
               "https://giphy.com.evil.example/a.gif", "https://user@evil.example/a.gif",
               "https://evilgiphy.com/a.gif", "javascript:alert(1)", None, 5]
        for url in good:
            self.assertIsNone(server.validate_outgoing_file("gif", {"url": url}), url)
        for url in bad:
            self.assertEqual(server.validate_outgoing_file("gif", {"url": url}), "Invalid GIF.", url)

    def test_reaction_length_is_capped(self):
        msg_id = server.save_message("Someone", "hello", "general", "text", sender_id="user-a")
        self.addCleanup(server.delete_message, msg_id, "user-a", True, "Test", None)
        client = server.socketio.test_client(server.app, headers=HEADERS)
        client.emit("join", {"room": "general"})
        client.get_received()
        client.emit("add_reaction", {"message_id": msg_id, "emoji": "x" * 5000})
        client.emit("add_reaction", {"message_id": msg_id, "emoji": ["👍"]})
        client.emit("add_reaction", {"message_id": msg_id, "emoji": "👍"})
        updates = [e for e in client.get_received() if e["name"] == "reaction_updated"]
        client.disconnect()
        self.assertEqual([u["args"][0]["emoji"] for u in updates], ["👍"])


if __name__ == "__main__":
    unittest.main()
