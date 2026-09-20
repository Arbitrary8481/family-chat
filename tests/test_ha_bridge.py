"""Tests for the Home Assistant -> Family Chat event bridge.

Run from the repository root with the standard library only:

    python -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'family-chat' / 'app'))

import ha_bridge  # noqa: E402
from ha_bridge import EventBridge, PostError, RateLimiter, parse_post_event, resolve_channel  # noqa: E402

CHANNELS = [
    {'slug': 'general', 'name': 'general'},
    {'slug': 'plans', 'name': 'family-plans'},
    {'slug': 'home-alerts', 'name': 'home-alerts'},
]


class ResolveChannelTests(unittest.TestCase):
    def test_matches_slug_or_display_name(self):
        self.assertEqual(resolve_channel('plans', CHANNELS), 'plans')
        self.assertEqual(resolve_channel('family-plans', CHANNELS), 'plans')

    def test_is_forgiving_about_case_hash_and_spacing(self):
        self.assertEqual(resolve_channel('#Home Alerts', CHANNELS), 'home-alerts')
        self.assertEqual(resolve_channel('  FAMILY_PLANS ', CHANNELS), 'plans')

    def test_unknown_channel_is_none_never_created(self):
        self.assertIsNone(resolve_channel('nope', CHANNELS))

    def test_no_channel_is_none_there_is_no_default(self):
        self.assertIsNone(resolve_channel(None, CHANNELS))
        self.assertIsNone(resolve_channel('', CHANNELS))

    def test_symbols_only_is_none(self):
        self.assertIsNone(resolve_channel('###', CHANNELS))


class ParseTests(unittest.TestCase):
    def test_minimal_event(self):
        self.assertEqual(parse_post_event({'channel': 'general', 'message': 'hi'}, CHANNELS),
                         ('general', 'Home Assistant', 'hi'))

    def test_channel_is_required_and_the_error_lists_the_real_ones(self):
        for data in ({'message': 'hi'}, {'message': 'hi', 'channel': ''}, {'message': 'hi', 'channel': '   '}):
            with self.assertRaises(PostError, msg=repr(data)) as ctx:
                parse_post_event(data, CHANNELS)
            self.assertIn('needs a "channel"', str(ctx.exception))
            for ch in CHANNELS:
                self.assertIn(ch['slug'], str(ctx.exception))

    def test_full_event(self):
        slug, sender, content = parse_post_event(
            {'channel': 'home-alerts', 'message': 'Door open', 'title': 'Freezer', 'sender': 'Freezer bot'},
            CHANNELS)
        self.assertEqual((slug, sender, content), ('home-alerts', 'Freezer bot', 'Freezer\nDoor open'))

    def test_numbers_are_accepted_as_text(self):
        # Home Assistant renders "{{ 5 }}" to a number, not a string.
        self.assertEqual(parse_post_event({'channel': 'general', 'message': 62}, CHANNELS)[2], '62')

    def test_control_characters_removed_but_newlines_kept(self):
        _, _, content = parse_post_event({'channel': 'general', 'message': 'a\x00b\x07c\nd\te'}, CHANNELS)
        self.assertEqual(content, 'abc\nd\te')

    def test_rejects_non_dict(self):
        for bad in (None, 'text', 5, ['message']):
            with self.assertRaises(PostError):
                parse_post_event(bad, CHANNELS)

    def test_rejects_missing_empty_or_structured_message(self):
        for data in ({'channel': 'general'}, {'channel': 'general', 'message': None},
                     {'channel': 'general', 'message': '   '}, {'channel': 'general', 'message': '\x00\x01'},
                     {'channel': 'general', 'message': {'a': 1}}, {'channel': 'general', 'message': ['a']}):
            with self.assertRaises(PostError, msg=repr(data)):
                parse_post_event(data, CHANNELS)

    def test_rejects_overlong_fields(self):
        with self.assertRaises(PostError):
            parse_post_event({'channel': 'general', 'message': 'x' * (ha_bridge.MAX_MESSAGE_LEN + 1)}, CHANNELS)
        with self.assertRaises(PostError):
            parse_post_event({'channel': 'general', 'message': 'ok', 'title': 'x' * (ha_bridge.MAX_TITLE_LEN + 1)}, CHANNELS)
        with self.assertRaises(PostError):
            parse_post_event({'channel': 'general', 'message': 'ok', 'sender': 'x' * (ha_bridge.MAX_SENDER_LEN + 1)}, CHANNELS)

    def test_message_at_the_limit_is_fine(self):
        parse_post_event({'channel': 'general', 'message': 'x' * ha_bridge.MAX_MESSAGE_LEN}, CHANNELS)

    def test_unknown_channel_error_lists_the_real_ones(self):
        with self.assertRaises(PostError) as ctx:
            parse_post_event({'channel': 'nope', 'message': 'hi'}, CHANNELS)
        text = str(ctx.exception)
        self.assertIn('nope', text)
        for ch in CHANNELS:
            self.assertIn(ch['slug'], text)


class RateLimiterTests(unittest.TestCase):
    def test_blocks_after_limit_and_recovers_after_window(self):
        now = [0.0]
        limiter = RateLimiter(count=3, window=10, clock=lambda: now[0])
        self.assertEqual([limiter.allow() for _ in range(4)], [True, True, True, False])
        now[0] = 9.9
        self.assertFalse(limiter.allow())
        now[0] = 10.0
        self.assertTrue(limiter.allow())


class Recorder:
    """Stand-ins for the server functions the bridge is given."""

    def __init__(self, post_error=None, report_error=None):
        self.posts, self.reports = [], []
        self._post_error, self._report_error = post_error, report_error

    def post_message(self, sender, content, channel):
        if self._post_error:
            raise self._post_error
        self.posts.append((sender, content, channel))
        return 100 + len(self.posts)

    def report_result(self, result):
        if self._report_error:
            raise self._report_error
        self.reports.append(result)


def make_bridge(rec, **kw):
    return EventBridge(token='SECRET-TOKEN', ws_url='ws://example/ws', get_channels=lambda: CHANNELS,
                       post_message=rec.post_message, report_result=rec.report_result, sleep=lambda s: None, **kw)


class HandleEventTests(unittest.TestCase):
    def test_success_posts_and_reports(self):
        rec = Recorder()
        result = make_bridge(rec).handle_event({'channel': 'plans', 'message': 'hi', 'request_id': 'r1'})
        self.assertEqual(rec.posts, [('Home Assistant', 'hi', 'plans')])
        self.assertEqual(result, {'ok': True, 'request_id': 'r1', 'channel': 'plans', 'message_id': 101})
        self.assertEqual(rec.reports, [result])

    def test_bad_event_is_refused_reported_and_not_posted(self):
        rec = Recorder()
        result = make_bridge(rec).handle_event({'channel': 'nope', 'message': 'hi'})
        self.assertFalse(result['ok'])
        self.assertIn('nope', result['error'])
        self.assertEqual(rec.posts, [])
        self.assertEqual(rec.reports, [result])

    def test_unexpected_error_is_contained_and_hides_details(self):
        rec = Recorder(post_error=RuntimeError('database exploded: /secret/path'))
        with self.assertLogs('family_chat.ha_bridge', level='ERROR'):
            result = make_bridge(rec).handle_event({'channel': 'general', 'message': 'hi'})
        self.assertFalse(result['ok'])
        self.assertNotIn('secret', result['error'])
        self.assertEqual(rec.reports, [result])

    def test_failure_to_report_does_not_raise(self):
        rec = Recorder(report_error=RuntimeError('HA unreachable'))
        with self.assertLogs('family_chat.ha_bridge', level='WARNING'):
            result = make_bridge(rec).handle_event({'channel': 'general', 'message': 'hi'})
        self.assertTrue(result['ok'])

    def test_rate_limit_drops_and_reports_excess(self):
        rec = Recorder()
        bridge = make_bridge(rec, rate_limiter=RateLimiter(count=2, window=60, clock=lambda: 0.0))
        results = [bridge.handle_event({'channel': 'general', 'message': f'm{i}'}) for i in range(3)]
        self.assertEqual([r['ok'] for r in results], [True, True, False])
        self.assertIn('Too many', results[2]['error'])
        self.assertEqual(len(rec.posts), 2)

    def test_non_dict_data_does_not_crash(self):
        rec = Recorder()
        self.assertFalse(make_bridge(rec).handle_event(None)['ok'])


class FakeWS:
    """A scripted WebSocket: incoming items are strings (returned by recv) or
    exceptions (raised by recv)."""

    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []
        self.closed = False

    def recv(self):
        item = self.incoming.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def send(self, data):
        self.sent.append(json.loads(data))

    def close(self):
        self.closed = True


class Stop(Exception):
    pass


def frames(*objs):
    return [json.dumps(o) for o in objs]


HANDSHAKE_OK = frames({'type': 'auth_required'}, {'type': 'auth_ok'}, {'type': 'result', 'id': 1, 'success': True})


class ConnectionTests(unittest.TestCase):
    def run_bridge(self, connections, rec=None):
        """Run the bridge over the given scripted connections; it stops when
        it tries to open one more than were provided."""
        rec = rec or Recorder()
        conns, sleeps = list(connections), []

        def connect(url):
            if not conns:
                raise Stop()
            return conns.pop(0)

        def sleep(seconds):
            sleeps.append(seconds)

        bridge = EventBridge(token='SECRET-TOKEN', ws_url='ws://example/ws', get_channels=lambda: CHANNELS,
                             post_message=rec.post_message, report_result=rec.report_result,
                             sleep=sleep, connect=connect)
        # The Stop raised by connect() escapes only via the sleep hook.
        original_sleep = bridge._sleep

        def stopping_sleep(seconds):
            original_sleep(seconds)
            if not conns:
                raise Stop()

        bridge._sleep = stopping_sleep
        with self.assertLogs('family_chat.ha_bridge', level='INFO') as logs:
            with self.assertRaises(Stop):
                bridge.run_forever()
        self.logs = '\n'.join(logs.output)
        return rec, sleeps

    def test_authenticates_subscribes_and_posts_events(self):
        event = {'type': 'event', 'id': 1, 'event': {'event_type': 'family_chat_post',
                                                     'data': {'channel': 'plans', 'message': 'hello'}}}
        other = {'type': 'event', 'id': 1, 'event': {'event_type': 'something_else', 'data': {'channel': 'general', 'message': 'no'}}}
        ws = FakeWS(HANDSHAKE_OK + frames(other, event) + [ConnectionError('dropped')])
        rec, sleeps = self.run_bridge([ws])

        self.assertEqual(ws.sent[0], {'type': 'auth', 'access_token': 'SECRET-TOKEN'})
        self.assertEqual(ws.sent[1], {'id': 1, 'type': 'subscribe_events', 'event_type': 'family_chat_post'})
        self.assertEqual(rec.posts, [('Home Assistant', 'hello', 'plans')])  # the other event ignored
        self.assertTrue(ws.closed)
        self.assertEqual(sleeps, [1])

    def test_reconnects_after_a_drop_and_resets_the_delay(self):
        first = FakeWS(HANDSHAKE_OK + [ConnectionError('dropped')])
        second = FakeWS(frames({'type': 'auth_required'}, {'type': 'auth_ok'}, {'type': 'result', 'id': 2, 'success': True})
                        + [ConnectionError('dropped again')])
        rec, sleeps = self.run_bridge([first, second])
        self.assertEqual(sleeps, [1, 1])  # each successful connect resets the back-off
        self.assertTrue(first.closed and second.closed)

    def test_rejected_token_backs_off_exponentially_and_caps(self):
        bad = lambda: FakeWS(frames({'type': 'auth_required'}, {'type': 'auth_invalid'}))  # noqa: E731
        rec, sleeps = self.run_bridge([bad() for _ in range(9)])
        self.assertEqual(sleeps, [1, 2, 4, 8, 16, 32, 60, 60, 60])

    def test_quiet_connection_sends_keepalive_ping(self):
        class WebSocketTimeoutException(Exception):  # same name the library uses
            pass

        ws = FakeWS(HANDSHAKE_OK + [WebSocketTimeoutException('quiet'), ConnectionError('dropped')])
        self.run_bridge([ws])
        pings = [m for m in ws.sent if m.get('type') == 'ping']
        self.assertEqual(len(pings), 1)

    def test_a_failing_handler_does_not_kill_the_connection(self):
        event = {'type': 'event', 'id': 1, 'event': {'event_type': 'family_chat_post', 'data': {'channel': 'general', 'message': 'a'}}}
        event2 = {'type': 'event', 'id': 1, 'event': {'event_type': 'family_chat_post', 'data': {'channel': 'general', 'message': 'b'}}}
        ws = FakeWS(HANDSHAKE_OK + frames(event, event2) + [ConnectionError('end')])

        class FlakyRec(Recorder):
            def post_message(self, sender, content, channel):
                if content == 'a':
                    raise RuntimeError('boom')
                return super().post_message(sender, content, channel)

        rec = FlakyRec()
        self.run_bridge([ws], rec=rec)
        self.assertEqual(rec.posts, [('Home Assistant', 'b', 'general')])
        self.assertIn('Unexpected error handling a family_chat_post event', self.logs)

    def test_token_never_appears_in_logs(self):
        ws = FakeWS(frames({'type': 'auth_required'}, {'type': 'auth_invalid'}))
        rec = Recorder()
        conns = [ws]

        def connect(url):
            if not conns:
                raise Stop()
            return conns.pop(0)

        def sleep(_):
            if not conns:
                raise Stop()

        bridge = EventBridge(token='SECRET-TOKEN', ws_url='ws://example/ws', get_channels=lambda: CHANNELS,
                             post_message=rec.post_message, report_result=rec.report_result,
                             sleep=sleep, connect=connect)
        with self.assertLogs('family_chat.ha_bridge', level='INFO') as logs:
            with self.assertRaises(Stop):
                bridge.run_forever()
        self.assertNotIn('SECRET-TOKEN', '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
