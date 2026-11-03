"""Tests for YouTube link previews (server.fetch_youtube_preview).

YouTube's oEmbed only answers for video links, so channel and /live links
fall back to reading the page. YouTube itself is never contacted: oEmbed
and the page fetch are replaced with stand-ins.

Needs the app's own dependencies (Flask etc.); skipped if they are missing.
Run from the repository root:

    python -m unittest discover -s tests -v
"""
import io
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

CHANNEL_LIVE = "https://www.youtube.com/channel/UCkphKNCtm1eh4MW_erzjocg/live"
STREAM = "https://www.youtube.com/watch?v=abc123XYZ_0"

# Roughly how YouTube lays out a page: a lot of inline script, then the
# canonical link and Open Graph tags further into the <head>.
FILLER = "<script>var ytcfg = {};" + ("x" * 300_000) + "</script>"

LIVE_PAGE = (
    "<html><head>" + FILLER +
    f'<link rel="canonical" href="{STREAM}">'
    '<meta property="og:title" content="Late night stream">'
    '<meta property="og:image" content="https://i.ytimg.com/vi/abc123XYZ_0/hqdefault_live.jpg">'
    "</head><body></body></html>"
)
OFFLINE_CHANNEL_PAGE = (
    "<html><head>" + FILLER +
    '<link rel="canonical" href="https://www.youtube.com/channel/UCkphKNCtm1eh4MW_erzjocg">'
    '<meta property="og:title" content="LEVYVERSE">'
    '<meta property="og:description" content="Streams and videos">'
    '<meta property="og:image" content="https://yt3.googleusercontent.com/avatar.jpg">'
    "</head><body></body></html>"
)


def oembed_for(known):
    """fetch_youtube_oembed stand-in that only knows the given video URLs,
    like the real one (a channel link gets a 404 there)."""
    def fake(url):
        if url in known:
            return {"url": url, "title": known[url], "description": "LEVYVERSE",
                    "image": "https://i.ytimg.com/vi/abc123XYZ_0/hqdefault.jpg", "site_name": "YouTube"}
        return None
    return fake


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class YouTubePreviewTests(unittest.TestCase):
    def preview(self, url, page, known):
        with mock.patch.object(server, "fetch_youtube_oembed", side_effect=oembed_for(known)), \
                mock.patch.object(server, "_fetch_page_head", return_value=page) as fetch:
            return server.fetch_youtube_preview(url), fetch

    def test_video_links_still_use_oembed_only(self):
        preview, fetch = self.preview(STREAM, None, {STREAM: "Late night stream"})
        self.assertEqual(preview["title"], "Late night stream")
        fetch.assert_not_called()

    def test_live_channel_link_previews_the_stream(self):
        preview, fetch = self.preview(CHANNEL_LIVE, LIVE_PAGE, {STREAM: "Late night stream"})
        self.assertEqual(preview["title"], "Late night stream")
        self.assertEqual(preview["description"], "LEVYVERSE")
        self.assertEqual(preview["url"], CHANNEL_LIVE)  # the link that was posted
        self.assertEqual(fetch.call_args.kwargs["max_bytes"], server.YOUTUBE_PAGE_MAX_BYTES)

    def test_live_page_falls_back_to_its_own_tags_if_oembed_fails(self):
        preview, _ = self.preview(CHANNEL_LIVE, LIVE_PAGE, {})
        self.assertEqual(preview["title"], "Late night stream")
        self.assertEqual(preview["site_name"], "YouTube")

    def test_offline_channel_shows_the_channel(self):
        preview, _ = self.preview(CHANNEL_LIVE, OFFLINE_CHANNEL_PAGE, {})
        self.assertEqual(preview["title"], "LEVYVERSE")
        self.assertEqual(preview["image"], "https://yt3.googleusercontent.com/avatar.jpg")
        self.assertEqual(preview["site_name"], "YouTube")

    def test_unreachable_page_gives_none(self):
        preview, _ = self.preview(CHANNEL_LIVE, None, {})
        self.assertIsNone(preview)

    def test_canonical_link_must_be_a_youtube_video(self):
        for href in ("https://evil.example/watch?v=abc", "http://www.youtube.com/watch?v=abc",
                     "https://www.youtube.com/channel/UCx", "https://www.youtube.com/watch"):
            with self.subTest(href=href):
                page = f'<html><head><link rel="canonical" href="{href}"></head></html>'
                self.assertIsNone(server._youtube_canonical_video_url(page))
        page = f'<html><head><link href="{STREAM}" rel="canonical"></head></html>'
        self.assertEqual(server._youtube_canonical_video_url(page), STREAM)


class _FakeResponse(io.BytesIO):
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class PageReadTests(unittest.TestCase):
    def read(self, body, max_bytes=65536):
        response = _FakeResponse(body.encode())
        with mock.patch.object(server._SAFE_URL_OPENER, "open", return_value=response):
            return server._fetch_page_head("https://example.com/", "test", max_bytes=max_bytes)

    def test_default_limit_is_unchanged(self):
        self.assertEqual(len(self.read("a" * 200_000)), 65536)

    def test_larger_limit_reads_further(self):
        self.assertEqual(len(self.read("a" * 200_000, max_bytes=150_000)), 150_000)

    def test_reading_stops_after_the_head(self):
        body = "<html><head>" + "a" * 70_000 + "</head><body>" + "b" * 500_000
        text = self.read(body, max_bytes=server.YOUTUBE_PAGE_MAX_BYTES)
        self.assertIn("</head>", text)
        self.assertLess(len(text), 200_000)

    def test_tags_deep_in_a_large_head_are_found(self):
        preview, _ = server._extract_preview(CHANNEL_LIVE, self.read(OFFLINE_CHANNEL_PAGE, server.YOUTUBE_PAGE_MAX_BYTES))
        self.assertEqual(preview["title"], "LEVYVERSE")


@unittest.skipIf(server is None, "the app's dependencies (Flask etc.) are not installed")
class HostilePageTests(unittest.TestCase):
    """A linked page is untrusted. Reading its tags must stay fast whatever
    it contains, because the server handles everyone on one thread. The old
    regular expressions took over six seconds on a 64 KB page like these."""

    def test_crafted_pages_are_read_quickly(self):
        import time
        units = ["<meta property=", "<link rel=", "<title>x", "<meta " + "a" * 2000 + ">",
                 '<meta a="' + ' b="' * 400 + '>', "<"]
        for unit in units:
            page = "<html><head>" + (unit * (1_000_000 // len(unit) + 1))[:1_000_000]
            with self.subTest(unit=unit[:20]):
                start = time.perf_counter()
                server._extract_preview("https://example.com/", page)
                server._youtube_canonical_video_url(page)
                self.assertLess(time.perf_counter() - start, 2.0)

    def test_attribute_order_and_quoting_do_not_matter(self):
        page = ("<html><head><TITLE>Plain</TITLE>"
                "<meta content='Reversed &amp; single' property=\"og:title\">"
                "<meta name=description content=bare>"
                "<meta property=og:image content=/a.png></head>")
        preview, has_og = server._extract_preview("https://example.com/page", page)
        self.assertTrue(has_og)
        self.assertEqual(preview["title"], "Reversed & single")
        self.assertEqual(preview["description"], "bare")
        self.assertEqual(preview["image"], "https://example.com/a.png")


if __name__ == "__main__":
    unittest.main()
