"""Lets Home Assistant automations post messages into Family Chat channels.

How it works
------------
An automation (usually through the ``script.family_chat_post`` helper, which
just wraps this) fires a Home Assistant event named ``family_chat_post``::

    event: family_chat_post
    event_data:
      channel: home-alerts    # required: slug or name of any existing channel
      message: "Freezer door has been open for 10 minutes"
      title: "Chest freezer"  # optional, shown on its own line above the message
      sender: "Freezer"       # optional display name, default "Home Assistant"

This module keeps a background connection to Home Assistant's WebSocket API
(through the Supervisor, authenticated with the app's own SUPERVISOR_TOKEN, so
there is no extra port, URL or secret to configure), listens for that event,
and hands each valid one to ``post_message`` -- which is the same pipeline a
person's message goes through, so unread counts, @mentions and each person's
own push-notification preferences all apply as they normally would.

After handling an event it fires ``family_chat_post_result`` back into Home
Assistant (``ok``, ``channel``, ``message_id`` / ``error``) so a failed post is
visible in the automation's trace and logbook instead of silently vanishing.

Delivery is best-effort, like the rest of Home Assistant's event bus: an event
fired while Family Chat or Home Assistant is restarting is not replayed. Keep
a second channel (e.g. a phone push) for alerts that must never be missed.

Everything in here is deliberately free of Flask/Socket.IO imports, so it can
be unit-tested on its own (see tests/test_ha_bridge.py).
"""
import json
import logging
import re
import time
from collections import deque

logger = logging.getLogger('family_chat.ha_bridge')

POST_EVENT = 'family_chat_post'
RESULT_EVENT = 'family_chat_post_result'

# Every message from Home Assistant carries this fixed sender id. It is not a
# Home Assistant user, so it never shows up in the member list or the
# @mention picker; the chat client uses it to label the message as a bot
# message, and it is what lets an admin or the owner delete one (the client
# only offers delete on a message that has a sender id) while nobody can edit
# one (edit is strictly sender-only).
BOT_SENDER_ID = 'ha-bot'
DEFAULT_SENDER = 'Home Assistant'

MAX_MESSAGE_LEN = 4000
MAX_TITLE_LEN = 100
MAX_SENDER_LEN = 40

# A misbehaving automation (say, one that re-triggers on every state change)
# should not be able to bury a channel. Counted across all channels.
RATE_LIMIT_COUNT = 30
RATE_LIMIT_WINDOW_SECONDS = 60

# Control characters other than tab and newline have no place in chat text.
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')


def _clean(value):
    return _CONTROL_CHARS.sub('', str(value)).strip()


def _normalize_channel_name(value):
    """'#Family Plans' -> 'family-plans', so 'family plans', 'family-plans'
    and '#family-plans' all mean the same channel."""
    value = str(value).strip().lstrip('#').lower()
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


def resolve_channel(requested, channels):
    """Find the channel slug for what the automation asked for -- either a
    channel's slug or its display name. Returns None if there is no such
    channel, or nothing was asked for. Only ever returns a slug that exists: a
    typo is refused rather than silently creating a new channel. There is
    deliberately no default channel -- an alert should never land somewhere the
    person who wrote the automation didn't choose."""
    if requested in (None, ''):
        return None
    wanted = _normalize_channel_name(requested)
    if not wanted:
        return None
    for ch in channels:
        if _normalize_channel_name(ch['slug']) == wanted:
            return ch['slug']
    for ch in channels:
        if _normalize_channel_name(ch['name']) == wanted:
            return ch['slug']
    return None


class PostError(ValueError):
    """The event was understood but can't be posted; the message is safe to
    show to whoever wrote the automation."""


def parse_post_event(data, channels):
    """Validate an event's data. Returns (channel_slug, sender, content) or
    raises PostError."""
    if not isinstance(data, dict):
        raise PostError('The event had no data. It needs a "channel" and a "message".')

    raw_message = data.get('message')
    if raw_message is None or isinstance(raw_message, (dict, list)):
        raise PostError('The event needs a "message" (text).')
    message = _clean(raw_message)
    if not message:
        raise PostError('The "message" was empty.')
    if len(message) > MAX_MESSAGE_LEN:
        raise PostError(f'The "message" is too long ({len(message)} characters; the limit is {MAX_MESSAGE_LEN}).')

    title = _clean(data.get('title') or '')
    if len(title) > MAX_TITLE_LEN:
        raise PostError(f'The "title" is too long (the limit is {MAX_TITLE_LEN} characters).')

    sender = _clean(data.get('sender') or '') or DEFAULT_SENDER
    if len(sender) > MAX_SENDER_LEN:
        raise PostError(f'The "sender" is too long (the limit is {MAX_SENDER_LEN} characters).')

    available = ', '.join(ch['slug'] for ch in channels) or 'none'
    asked = _clean(data.get('channel') or '')
    if not asked:
        raise PostError(f'The event needs a "channel". Existing channels: {available}.')
    slug = resolve_channel(asked, channels)
    if slug is None:
        raise PostError(f'There is no channel "{asked}". Existing channels: {available}.')

    content = f'{title}\n{message}' if title else message
    return slug, sender, content


class RateLimiter:
    def __init__(self, count=RATE_LIMIT_COUNT, window=RATE_LIMIT_WINDOW_SECONDS, clock=time.monotonic):
        self._count = count
        self._window = window
        self._clock = clock
        self._hits = deque()

    def allow(self):
        now = self._clock()
        while self._hits and now - self._hits[0] >= self._window:
            self._hits.popleft()
        if len(self._hits) >= self._count:
            return False
        self._hits.append(now)
        return True


class EventBridge:
    def __init__(self, *, token, ws_url, get_channels, post_message, report_result,
                 spawn=None, sleep=time.sleep, connect=None, rate_limiter=None):
        """
        token           Home Assistant access token (the Supervisor token in an app).
        ws_url          Home Assistant's WebSocket endpoint.
        get_channels    () -> [{'slug', 'name', ...}]   the channels that exist right now.
        post_message    (sender, content, channel_slug) -> message id.
        report_result   (dict) -> None; fires RESULT_EVENT back into Home Assistant.
        spawn           (fn, *args) -> None; runs fn concurrently so one slow post can't
                        stall the listener. Defaults to calling it directly.
        connect         (url) -> connection object with recv/send/close/settimeout;
                        defaults to the websocket-client library.
        """
        self._token = token
        self._ws_url = ws_url
        self._get_channels = get_channels
        self._post_message = post_message
        self._report_result = report_result
        self._spawn = spawn or (lambda fn, *a: fn(*a))
        self._sleep = sleep
        self._connect = connect or self._default_connect
        self._limiter = rate_limiter or RateLimiter()
        self._next_id = 1

    # -- handling one event (no network in here except post/report) --------

    def handle_event(self, data):
        """Post one event and report what happened. Never raises."""
        request_id = data.get('request_id') if isinstance(data, dict) else None
        result = {'ok': False, 'request_id': request_id}
        try:
            if not self._limiter.allow():
                raise PostError(
                    f'Too many messages (more than {RATE_LIMIT_COUNT} in {RATE_LIMIT_WINDOW_SECONDS} seconds); this one was dropped.')
            slug, sender, content = parse_post_event(data, self._get_channels())
            message_id = self._post_message(sender, content, slug)
            result.update(ok=True, channel=slug, message_id=message_id)
        except PostError as e:
            result['error'] = str(e)
            logger.warning('Refused a Home Assistant post: %s', e)
        except Exception:  # noqa: BLE001 - a bad event must never take the bridge down
            result['error'] = 'Family Chat hit an internal error posting that message; see the app log.'
            logger.exception('Unexpected error handling a %s event', POST_EVENT)
        try:
            self._report_result(result)
        except Exception:  # noqa: BLE001
            logger.warning('Could not report the result of a post back to Home Assistant', exc_info=True)
        return result

    # -- the connection ----------------------------------------------------

    @staticmethod
    def _default_connect(url):
        import websocket  # websocket-client; imported lazily so tests don't need it
        return websocket.create_connection(url, timeout=30)

    def _send(self, ws, payload):
        ws.send(json.dumps(payload))

    def _recv_json(self, ws):
        raw = ws.recv()
        if not raw:
            raise ConnectionError('Home Assistant closed the connection.')
        return json.loads(raw)

    def _handshake(self, ws):
        hello = self._recv_json(ws)
        if hello.get('type') != 'auth_required':
            raise ConnectionError(f'Unexpected first message from Home Assistant: {hello.get("type")!r}')
        self._send(ws, {'type': 'auth', 'access_token': self._token})
        reply = self._recv_json(ws)
        if reply.get('type') != 'auth_ok':
            raise ConnectionError(f'Home Assistant did not accept the token ({reply.get("type")!r}).')

        sub_id = self._next_id
        self._next_id += 1
        self._send(ws, {'id': sub_id, 'type': 'subscribe_events', 'event_type': POST_EVENT})
        while True:  # the result may be preceded by other frames; wait for ours
            msg = self._recv_json(ws)
            if msg.get('type') == 'result' and msg.get('id') == sub_id:
                if not msg.get('success'):
                    raise ConnectionError('Home Assistant refused the event subscription.')
                return

    def _listen(self, ws):
        """Runs until the connection drops (raises). A quiet socket times out
        every so often, which is used as the cue to send a keep-alive ping."""
        while True:
            try:
                msg = self._recv_json(ws)
            except Exception as e:  # noqa: BLE001
                if isinstance(e, TimeoutError) or type(e).__name__ == 'WebSocketTimeoutException':
                    ping_id = self._next_id
                    self._next_id += 1
                    self._send(ws, {'id': ping_id, 'type': 'ping'})
                    continue
                raise
            if msg.get('type') == 'event':
                event = msg.get('event') or {}
                if event.get('event_type') == POST_EVENT:
                    self._spawn(self.handle_event, event.get('data'))

    def run_forever(self):
        """Connect, listen, and reconnect (with growing pauses, up to a
        minute) whenever the connection drops -- Home Assistant restarting is
        routine. Never returns."""
        delay = 1
        while True:
            ws = None
            try:
                ws = self._connect(self._ws_url)
                self._handshake(ws)
                logger.info('Listening for "%s" events from Home Assistant', POST_EVENT)
                delay = 1
                self._listen(ws)
            except Exception as e:  # noqa: BLE001
                logger.warning('Home Assistant event connection lost (%s: %s); retrying in %ss',
                               type(e).__name__, e, delay)
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:  # noqa: BLE001
                        pass
            self._sleep(delay)
            delay = min(delay * 2, 60)
