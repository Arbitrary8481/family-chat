"""Tests for link-preview fetching (server.fetch_open_graph_preview).

A tiny local web server plays the part of real sites that treat a
browser-looking request differently from an honest link previewer:

  facebook-like   HTTP 400 to a browser, real Open Graph tags to a previewer
  instagram-like  200 with a login wall (no tags) to a browser, real tags to a previewer

Needs the app's own dependencies (Flask etc. - `pip install -r
family-chat/app/requirements.txt`); the whole module is skipped if they are
missing. Run from the repository root:

    python -m unittest discover -s tests -v
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The server module creates its data folder at import time; give it a scratch
# one so the tests never touch real data.
_SCRATCH = tempfile.mkdtemp(prefix="family-chat-tests-")
os.environ.setdefault("FAMILY_CHAT_DATA_DIR", _SCRATCH)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "family-chat" / "app"))

try:
    import logging
    import server  # noqa: E402
except ImportError as e:  # pragma: no cover - depends on the environment
    server = None
    _IMPORT_ERROR = str(e)

OG_PAGE = (
    '<html><head><title>Plain title</title>'
    '<meta property="og:title" content="OG Title">'
    '<meta property="og:description" content="OG description">'
    '<meta property="og:image" content="/img/card.png">'
    '<meta property="og:site_name" content="Some Site"></head><body>x</body></html>'
)
LOGIN_WALL = '<html><head><title>Log in to continue</title></head><body>please log in</body></html>'
PLAIN_ONLY = ('<html><head><title>Just a title</title>'
              '<meta name="description" content="Just a description"></head><body>x</body></html>')
NOTHING = '<html><head></head><body>nothing to preview</body></html>'
# Attribute values arrive HTML-escaped, exactly as Facebook and Instagram send them.
ENTITY_OG_PAGE = (
    '<html><head>'
    '<meta property="og:title" content="NASA (&#064;nasa) &#x2022; Tom &amp; Jerry">'
    '<meta property="og:description" content="28,726,756 followers &#xb7; talking &amp;   more">'
    '<meta property="og:image" content="/i.png?a=1&amp;b=2&amp;c=3">'
    '<meta property="og:site_name" content="Fish &amp; Chips"></head></html>'
)
ENTITY_PLAIN_PAGE = ('<html><head><title>Tom &amp; Jerry</title>'
                     '<meta name="description" content="Buy &amp; sell &#x2022; cards"></head></html>')


# The fake site runs in its own process. Importing the app's server module
# applies eventlet's monkey-patching to this process, which breaks a plain
# threaded test web server living inside it. It records every request as a
# "path<TAB>user-agent" line in a log file, which the tests read back.
FAKE_SITE = r'''
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

OG_PAGE = """__OG_PAGE__"""
LOGIN_WALL = """__LOGIN_WALL__"""
PLAIN_ONLY = """__PLAIN_ONLY__"""
NOTHING = """__NOTHING__"""
ENTITY_OG_PAGE = """__ENTITY_OG_PAGE__"""
ENTITY_PLAIN_PAGE = """__ENTITY_PLAIN_PAGE__"""
LOG = sys.argv[1]

def is_previewer(ua):
    return "FamilyChatLinkPreview" in ua

ROUTES = {
    "/ordinary":  lambda ua: (200, "text/html", OG_PAGE),
    "/facebook":  lambda ua: (200, "text/html", OG_PAGE) if is_previewer(ua) else (400, "text/html", ""),
    "/instagram": lambda ua: (200, "text/html", OG_PAGE) if is_previewer(ua) else (200, "text/html", LOGIN_WALL),
    "/plain":     lambda ua: (200, "text/html", PLAIN_ONLY),
    "/blocked":   lambda ua: (403, "text/html", "no"),
    "/nothing":   lambda ua: (200, "text/html", NOTHING),
    "/json":      lambda ua: (200, "application/json", '{"a": 1}'),
    "/entities":  lambda ua: (200, "text/html", ENTITY_OG_PAGE),
    "/entities_plain": lambda ua: (200, "text/html", ENTITY_PLAIN_PAGE),
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        ua = self.headers.get("User-Agent", "")
        with open(LOG, "a") as f:
            f.write(self.path + "\t" + ua + "\n")
        route = ROUTES.get(self.path)
        status, ctype, body = route(ua) if route else (404, "text/plain", "")
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass

httpd = HTTPServer(("127.0.0.1", 0), Handler)
print(httpd.server_address[1], flush=True)
httpd.serve_forever()
'''
for _name, _value in (("__OG_PAGE__", OG_PAGE), ("__LOGIN_WALL__", LOGIN_WALL),
                      ("__PLAIN_ONLY__", PLAIN_ONLY), ("__NOTHING__", NOTHING),
                      ("__ENTITY_OG_PAGE__", ENTITY_OG_PAGE), ("__ENTITY_PLAIN_PAGE__", ENTITY_PLAIN_PAGE)):
    FAKE_SITE = FAKE_SITE.replace(_name, _value)


def is_previewer(user_agent):
    return "FamilyChatLinkPreview" in user_agent


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class FetchPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = os.path.join(_SCRATCH, "requests.log")
        cls.proc = subprocess.Popen([sys.executable, "-c", FAKE_SITE, cls.log],
                                    stdout=subprocess.PIPE, text=True)
        cls.base = f"http://127.0.0.1:{int(cls.proc.stdout.readline())}"

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)

    def setUp(self):
        open(self.log, "w").close()
        # The fetcher logs each failed attempt; that is expected here. Scoped to
        # these tests so it can't affect any other test module's log assertions.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    @property
    def requests(self):
        with open(self.log) as f:
            return [tuple(line.rstrip("\n").split("\t", 1)) for line in f if line.strip()]

    def fetch(self, path):
        return server.fetch_open_graph_preview(self.base + path)

    def test_ordinary_site_costs_one_request_and_never_uses_the_previewer_identity(self):
        preview = self.fetch("/ordinary")
        self.assertEqual(preview["title"], "OG Title")
        self.assertEqual(preview["description"], "OG description")
        self.assertEqual(preview["site_name"], "Some Site")
        self.assertEqual(preview["image"], self.base + "/img/card.png")  # relative og:image resolved
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(is_previewer(self.requests[0][1]))

    def test_facebook_style_400_to_a_browser_is_recovered_by_the_previewer_identity(self):
        preview = self.fetch("/facebook")
        self.assertEqual(preview["title"], "OG Title")
        self.assertEqual([is_previewer(ua) for _, ua in self.requests], [False, True])

    def test_instagram_style_login_wall_loses_to_real_open_graph_tags(self):
        preview = self.fetch("/instagram")
        self.assertEqual(preview["title"], "OG Title")  # not "Log in to continue"
        self.assertEqual(len(self.requests), 2)

    def test_a_page_with_only_a_plain_title_still_previews_from_that_title(self):
        preview = self.fetch("/plain")
        self.assertEqual(preview["title"], "Just a title")
        self.assertEqual(preview["description"], "Just a description")
        self.assertEqual(len(self.requests), 2)  # the second identity was tried and had nothing better

    def test_a_site_that_blocks_everyone_gives_none(self):
        self.assertIsNone(self.fetch("/blocked"))
        self.assertEqual(len(self.requests), 2)

    def test_a_page_with_nothing_to_show_gives_none(self):
        self.assertIsNone(self.fetch("/nothing"))

    def test_html_entities_in_open_graph_values_are_decoded(self):
        preview = self.fetch("/entities")
        self.assertEqual(preview["title"], "NASA (@nasa) \u2022 Tom & Jerry")
        self.assertEqual(preview["description"], "28,726,756 followers \u00b7 talking & more")  # whitespace collapsed
        self.assertEqual(preview["site_name"], "Fish & Chips")

    def test_og_image_url_query_string_is_not_corrupted_by_entities(self):
        preview = self.fetch("/entities")
        self.assertEqual(preview["image"], self.base + "/i.png?a=1&b=2&c=3")
        self.assertNotIn("&amp;", preview["image"])

    def test_html_entities_in_the_plain_title_and_description_are_decoded(self):
        preview = self.fetch("/entities_plain")
        self.assertEqual(preview["title"], "Tom & Jerry")
        self.assertEqual(preview["description"], "Buy & sell \u2022 cards")

    def test_non_html_is_never_previewed(self):
        self.assertIsNone(self.fetch("/json"))

    def test_the_previewer_identity_announces_itself_honestly(self):
        self.fetch("/facebook")
        previewer_ua = self.requests[-1][1]
        self.assertIn("FamilyChatLinkPreview", previewer_ua)
        for other in ("facebookexternalhit", "Twitterbot", "Discordbot", "Slackbot", "Googlebot"):
            self.assertNotIn(other, previewer_ua)  # never borrows another company's crawler name


if __name__ == "__main__":
    unittest.main()
