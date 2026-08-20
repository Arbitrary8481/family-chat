#!/usr/bin/env python3
# eventlet.monkey_patch() has to run before anything else imports the
# stdlib modules it patches (socket, select, ssl, os, threading, time,
# ...) — importing e.g. sqlite3 or urllib first would leave those
# holding references to the real, blocking implementations, defeating
# the patch for exactly the code that needs it most.
import eventlet
eventlet.monkey_patch()

import asyncio
import functools
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import base64
import hashlib
import traceback
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('family_chat')

app = Flask(__name__, template_folder='templates', static_folder='static')
# async_mode='eventlet' — briefly switched to 'threading' (2.20.0) to
# get off eventlet, which is deprecated upstream, but that broke real
# functionality: Flask-SocketIO's threading mode runs on Werkzeug's
# plain dev server, which has no native WebSocket support at all —
# every client falls back to HTTP long-polling, visible in the log as
# the same session id making a new /socket.io/ request every ~150ms,
# eventually followed by "Session is disconnected". Confirmed directly
# by Flask-SocketIO's own maintainer: threading mode works "without
# WebSocket for now." Eventlet's own WSGI server has genuine WebSocket
# support built in, which is what this app actually needs for real-time
# delivery to feel real-time rather than constant re-polling. Back on
# eventlet until there's a properly-tested alternative that doesn't
# regress this (e.g. threading mode + the simple-websocket package,
# which the same discussion mentions but with mixed reliability reports
# — not something to switch to without dedicated testing first).
# logger=True surfaces Socket.IO's own connect/disconnect/event activity in
# the log too, which is useful context alongside our own error logging below.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True)

# Home Assistant writes add-on options to /data/options.json regardless of
# base image. This app never read it (run.sh just hardcoded env vars
# instead), so config.yaml options were silently ignored. Reading the file
# directly here makes username1/username2/theme/admin_password actually
# take effect, and still falls back to env vars for local/non-HA runs.
def _load_ha_options():
    options_file = Path('/data/options.json')
    if options_file.exists():
        try:
            with open(options_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

_ha_options = _load_ha_options()

def get_option(key, env_key, default):
    if key in _ha_options and _ha_options[key] not in (None, ''):
        return _ha_options[key]
    return os.environ.get(env_key, default)

# Persist a random Flask session secret across restarts instead of using a
# hardcoded one (a hardcoded SECRET_KEY breaks session/cookie integrity,
# which matters now that the admin panel relies on signed session cookies).
_SECRET_KEY_FILE = Path('/data/secret_key')
if _SECRET_KEY_FILE.exists():
    app.config['SECRET_KEY'] = _SECRET_KEY_FILE.read_text().strip()
else:
    new_secret = secrets.token_hex(32)
    _SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_KEY_FILE.write_text(new_secret)
    app.config['SECRET_KEY'] = new_secret

# CodeQL flags the write above as "clear-text storage of sensitive
# information," and its literal suggestion (encrypt it) doesn't really
# apply here — this *is* the key; encrypting it would just mean
# persisting a second key to decrypt the first, which moves the problem
# rather than solving it. What actually matters for a signing key like
# this is restricting who can read the file at the OS level: only the
# owning user, not any other process on the host or anyone with read
# access to a filesystem-level backup. Applied unconditionally (not just
# when the file is first created) so it also retroactively covers a file
# an older version of this add-on already created before this existed.
try:
    _SECRET_KEY_FILE.chmod(0o600)
except OSError as e:
    logger.warning('Could not restrict permissions on %s: %s', _SECRET_KEY_FILE, e)

# Signed cookies (the session cookie, which is what the admin panel and
# nothing else in this app relies on) should never be sent over plain
# HTTP to a different site, or be readable by page JavaScript.
# SESSION_COOKIE_SECURE is deliberately left at Flask's default (off)
# rather than forced on: Home Assistant's ingress commonly terminates
# TLS upstream and proxies to this add-on over plain HTTP internally, so
# forcing Secure here would silently break the admin session entirely
# on the (very common) HA setup that isn't itself served over HTTPS.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configuration
THEME = get_option('theme', 'THEME', 'dark')
# Was previously read straight from an env var, bypassing get_option
# entirely — meaning the max_file_size option in the add-on's own
# configuration screen was silently ignored no matter what it was set
# to, and (see MAX_CONTENT_LENGTH below) wasn't actually enforced
# anywhere regardless.
MAX_FILE_SIZE = int(get_option('max_file_size', 'MAX_FILE_SIZE', 25)) * 1024 * 1024
# Flask rejects any request body over this size outright (413), before
# ever reading it into memory — this is what actually makes
# max_file_size mean something, rather than every upload being capped
# at a hardcoded 100MB regardless of what's configured. The padding
# accounts for multipart form overhead (boundaries, headers, the other
# non-file fields in the request) on top of the file content itself.
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE + (1 * 1024 * 1024)

ADMIN_PASSWORD = get_option('admin_password', 'ADMIN_PASSWORD', 'changeme')
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)
if ADMIN_PASSWORD == 'changeme':
    logger.warning('admin_password is still set to the default "changeme". '
                    'Set it in the add-on configuration.')

# Very small in-memory brute-force guard for the admin login form —
# previously unlimited, meaning an automated script could try passwords
# as fast as the network/CPU allowed. Deliberately NOT scoped per-IP:
# this app sits behind Home Assistant's ingress proxy, which may or may
# not forward the real client address depending on setup, so per-IP
# tracking could either do nothing (if every request looks like it's
# from the same internal proxy address) or accidentally lock out the
# whole family sharing one apparent address. There's exactly one admin
# password shared by trusted family members anyway, so a global cooldown
# after repeated failures is an acceptable trade-off: it meaningfully
# raises the bar against automated guessing, at the cost of (rarely)
# also delaying a legitimate next attempt for a few minutes.
_admin_login_failures = []
_ADMIN_LOGIN_MAX_FAILURES = 10
_ADMIN_LOGIN_WINDOW_SECONDS = 300

def _admin_login_rate_limited():
    cutoff = datetime.now().timestamp() - _ADMIN_LOGIN_WINDOW_SECONDS
    while _admin_login_failures and _admin_login_failures[0] < cutoff:
        _admin_login_failures.pop(0)
    return len(_admin_login_failures) >= _ADMIN_LOGIN_MAX_FAILURES

# GIPHY API key, kept server-side only — the browser talks to /api/giphy/*
# on this server, which forwards to GIPHY with the key attached. The key
# never appears in any response sent to the client.
GIPHY_API_KEY = get_option('giphy_api_key', 'GIPHY_API_KEY', '')
if not GIPHY_API_KEY:
    logger.warning('giphy_api_key is not set — the GIF picker will be disabled '
                    'until one is added in the add-on configuration.')

# Supervisor injects this automatically once the add-on has
# `homeassistant_api: true` in config.yaml, and it's what lets this add-on
# call Home Assistant's own REST API (proxied through the supervisor at
# http://supervisor/core/api/...) to trigger notify.* services — no
# separate push infrastructure of our own, no API key to configure. If
# that permission hasn't been granted (or the add-on hasn't been rebuilt
# since it was added), this is simply unset and notifications quietly
# stay unavailable rather than erroring.
SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')
if not SUPERVISOR_TOKEN:
    logger.warning('SUPERVISOR_TOKEN is not set — Home Assistant notifications will be '
                    'unavailable until this add-on is rebuilt with homeassistant_api access.')

# Cache-busting token for static assets (CSS/JS). This used to be
# computed once at process start, changing only on a container restart
# — which turned out not to be aggressive enough. Home Assistant's
# ingress iframe layer has now shown a pattern, across several separate
# incidents in this app's history, of not reliably honoring
# Cache-Control: no-store (see set_cache_headers()'s own comment for
# the earlier ones) — the *only* thing that reliably defeats a cache
# that ignores headers entirely is a URL that's never the same twice,
# which a once-per-restart version string doesn't provide: every page
# load within a session requested the exact same script.js?v=... URL,
# giving a header-ignoring cache something consistent to keep matching
# and re-serving stale. Computed fresh per request instead now — see
# index() — the same "unique on every load, not just every deploy"
# approach already used for this app's own fetch() calls.

# Inlined directly into index.html (see below) instead of served as a
# separate <link rel="stylesheet"> request. Home Assistant's ingress
# "soft" panel reload occasionally lets sub-resource requests (like the
# CSS file) race against the ingress session still being established,
# which can make the stylesheet fail to load until a manual refresh.
# Inlining it removes that race entirely — if the HTML document loaded at
# all, the styles are already in it, no second request required.
_STYLE_CSS_PATH = Path(__file__).parent / 'static' / 'style.css'
INLINE_CSS = _STYLE_CSS_PATH.read_text() if _STYLE_CSS_PATH.exists() else ''

# Upload directory
UPLOAD_FOLDER = Path('/data/uploads')
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mp3',
    'wav', 'pdf', 'txt', 'md', 'doc', 'docx'
}
ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database setup
def init_db():
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    
    # Messages table with file support
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  content TEXT,
                  timestamp TEXT NOT NULL,
                  channel TEXT DEFAULT 'general',
                  message_type TEXT DEFAULT 'text',
                  file_url TEXT,
                  file_name TEXT,
                  file_size INTEGER,
                  mime_type TEXT,
                  sender_id TEXT)''')
    # sender_id didn't exist in older versions — add it if this DB predates
    # the alias feature, so existing installs upgrade without losing data.
    c.execute("PRAGMA table_info(messages)")
    if 'sender_id' not in [col[1] for col in c.fetchall()]:
        c.execute('ALTER TABLE messages ADD COLUMN sender_id TEXT')

    # Display name aliases, keyed by the stable Home Assistant user ID (not
    # by name, since names can change). Looked up at read time so renaming
    # someone updates every message they've ever sent, not just future
    # ones — see get_messages() and resolve_ha_identity().
    c.execute('''CREATE TABLE IF NOT EXISTS user_aliases
                 (user_id TEXT PRIMARY KEY, alias TEXT NOT NULL)''')

    # Self-service avatars, same keying and same "looked up at read time"
    # reasoning as user_aliases above — setting a new avatar picture
    # updates it on every past message too, not just future ones.
    c.execute('''CREATE TABLE IF NOT EXISTS user_avatars
                 (user_id TEXT PRIMARY KEY, avatar_url TEXT NOT NULL)''')

    # Tracks which calendar events were created through this app and by
    # whom — calendar.create_event doesn't hand back the new event's uid
    # in its response, so this gets populated by looking the event back
    # up right after creating it (see find_event_uid()). Events added
    # directly in Home Assistant, outside this app, simply won't have a
    # row here — the "Upcoming" panel shows them anyway, just without a
    # "added by" attribution, since that's not something HA itself
    # tracks and isn't knowable after the fact.
    c.execute('''CREATE TABLE IF NOT EXISTS calendar_event_log
                 (uid TEXT NOT NULL,
                  entity_id TEXT NOT NULL,
                  created_by_id TEXT,
                  created_by_name TEXT,
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (uid, entity_id))''')

    # One row per (person, channel, message) they were @mentioned in and
    # haven't yet seen — rows get deleted wholesale for a channel the
    # moment that person actually views it, so a channel's count is
    # always just "how many rows are still here". Persisted rather than
    # tracked purely client-side/in-memory so it survives a reload, a
    # different device, or having been offline when the mention
    # actually happened — the same reasoning notify_message_subscribers()
    # already uses for push notifications.
    c.execute('''CREATE TABLE IF NOT EXISTS unread_mentions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  channel TEXT NOT NULL,
                  message_id INTEGER NOT NULL,
                  created_at TEXT NOT NULL)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_unread_mentions_user_channel ON unread_mentions(user_id, channel)')

    # A much simpler cousin of unread_mentions — one row per person per
    # channel, just "the highest message id you'd seen last time you
    # looked". A channel counts as having unread activity if it has any
    # message with a higher id than this, sent by someone other than
    # you. No per-message rows to accumulate here, unlike mentions,
    # since this only ever needs "is there anything newer", never a
    # count.
    c.execute('''CREATE TABLE IF NOT EXISTS channel_last_read
                 (user_id TEXT NOT NULL,
                  channel TEXT NOT NULL,
                  last_read_message_id INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY (user_id, channel))''')

    # Custom emojis table
    c.execute('''CREATE TABLE IF NOT EXISTS custom_emojis
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  file_path TEXT NOT NULL,
                  created_by TEXT,
                  created_at TEXT)''')
    
    # Reactions table
    c.execute('''CREATE TABLE IF NOT EXISTS reactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  message_id INTEGER,
                  emoji TEXT,
                  user TEXT,
                  FOREIGN KEY (message_id) REFERENCES messages(id))''')

    # Settings table (currently: display names for the two family members).
    # Seeded once from add-on options/env vars, then editable from /admin
    # without needing a container restart.
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT NOT NULL)''')

    # Home Assistant users seen via ingress auth headers, so the admin
    # panel can offer "when this HA account is logged in, auto-sign-in as
    # <family member>" without the add-on needing to talk to HA's auth API.
    c.execute('''CREATE TABLE IF NOT EXISTS ha_users
                 (user_id TEXT PRIMARY KEY,
                  username TEXT,
                  display_name TEXT,
                  last_seen TEXT)''')

    # Channels — used to be four hardcoded entries in the HTML template.
    # Seeded with those same four defaults so nothing changes for existing
    # installs; from here on they're managed from the admin panel.
    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  slug TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  icon TEXT NOT NULL DEFAULT '#')''')
    c.execute('SELECT COUNT(*) FROM channels')
    if c.fetchone()[0] == 0:
        c.executemany(
            'INSERT INTO channels (slug, name, icon) VALUES (?, ?, ?)',
            [
                ('general', 'general', '#'),
                ('plans', 'family-plans', '#'),
                ('memories', 'memories', '📸'),
                ('files', 'shared-files', '📁'),
            ]
        )

    # Channel categories — sidebar section headers a channel belongs
    # under (Discord-style). Only an admin can create one; anyone can
    # still add a channel, but only into a category that already
    # exists.
    c.execute('''CREATE TABLE IF NOT EXISTS channel_categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  created_at TEXT NOT NULL)''')

    c.execute("PRAGMA table_info(channels)")
    if 'category_id' not in [col[1] for col in c.fetchall()]:
        c.execute('ALTER TABLE channels ADD COLUMN category_id INTEGER')

    # Added after channels already existed, on every install — nothing
    # created before this point has a category yet, and the sidebar now
    # always groups by category rather than falling back to a flat
    # list, so every existing channel needs a real home rather than
    # silently becoming invisible. Only creates the fallback category
    # if it's actually needed for something.
    c.execute('SELECT COUNT(*) FROM channels WHERE category_id IS NULL')
    if c.fetchone()[0] > 0:
        c.execute('SELECT id FROM channel_categories WHERE name = ?', ('General',))
        row = c.fetchone()
        if row:
            default_category_id = row[0]
        else:
            c.execute('INSERT INTO channel_categories (name, created_at) VALUES (?, ?)',
                       ('General', datetime.now().isoformat()))
            default_category_id = c.lastrowid
        c.execute('UPDATE channels SET category_id = ? WHERE category_id IS NULL', (default_category_id,))

    # Explicit sort order for reordering categories/channels — id order
    # alone can't represent an arbitrary admin-chosen order, only ever
    # "in the order they were created". Backfilled from whatever the
    # current id-based order already was, so a reorder feature added
    # after the fact doesn't silently reshuffle anything on upgrade.
    c.execute("PRAGMA table_info(channel_categories)")
    if 'position' not in [col[1] for col in c.fetchall()]:
        c.execute('ALTER TABLE channel_categories ADD COLUMN position INTEGER')
        c.execute('SELECT id FROM channel_categories ORDER BY id ASC')
        for i, (cat_id,) in enumerate(c.fetchall()):
            c.execute('UPDATE channel_categories SET position = ? WHERE id = ?', (i, cat_id))

    c.execute("PRAGMA table_info(channels)")
    if 'position' not in [col[1] for col in c.fetchall()]:
        c.execute('ALTER TABLE channels ADD COLUMN position INTEGER')
        # Position is scoped within a category (a channel only ever
        # moves among its own siblings, not across categories), so each
        # category's channels get their own independent 0, 1, 2...
        # sequence rather than one shared across the whole table.
        c.execute('SELECT DISTINCT category_id FROM channels')
        for (cat_id,) in c.fetchall():
            c.execute('SELECT id FROM channels WHERE category_id = ? ORDER BY id ASC', (cat_id,))
            for i, (ch_id,) in enumerate(c.fetchall()):
                c.execute('UPDATE channels SET position = ? WHERE id = ?', (i, ch_id))

    # Per-person notification preference, keyed by the same stable HA user
    # ID used everywhere else. notify_service is a Home Assistant
    # notify.* service name (e.g. "mobile_app_johns_iphone") created
    # automatically by the HA Companion App on that person's phone —
    # picked from a list fetched from HA rather than typed by hand. Push
    # delivery itself is entirely Home Assistant's; this add-on only
    # decides *whether* and *where* to call notify.<service> when a
    # message comes in — see notify_message_subscribers(). The `enabled`
    # column is a leftover from before per-channel subscriptions existed
    # (see notification_channel_subs below) — it's no longer read when
    # deciding who to notify, only during the one-time migration just
    # after this table, so it stays here rather than risking an ALTER
    # TABLE DROP COLUMN against installs already running the old schema.
    c.execute('''CREATE TABLE IF NOT EXISTS notification_prefs
                 (user_id TEXT PRIMARY KEY,
                  enabled INTEGER NOT NULL DEFAULT 0,
                  notify_service TEXT)''')

    # Which channels each person actually wants a notification for.
    # Presence of a row is the subscription itself — no separate on/off
    # flag needed per channel.
    c.execute('''CREATE TABLE IF NOT EXISTS notification_channel_subs
                 (user_id TEXT NOT NULL,
                  channel TEXT NOT NULL,
                  PRIMARY KEY (user_id, channel))''')

    # One-time migration: anyone who turned on the old all-channels
    # toggle before per-channel subscriptions existed gets subscribed to
    # every channel that exists right now, so upgrading doesn't silently
    # turn notifications off for them — they can narrow it down from
    # Settings afterward.
    c.execute('SELECT user_id FROM notification_prefs WHERE enabled = 1')
    legacy_enabled_users = [row[0] for row in c.fetchall()]
    if legacy_enabled_users:
        c.execute('SELECT slug FROM channels')
        all_slugs = [row[0] for row in c.fetchall()]
        for user_id in legacy_enabled_users:
            c.execute('SELECT COUNT(*) FROM notification_channel_subs WHERE user_id = ?', (user_id,))
            if c.fetchone()[0] == 0 and all_slugs:
                c.executemany(
                    'INSERT OR IGNORE INTO notification_channel_subs (user_id, channel) VALUES (?, ?)',
                    [(user_id, slug) for slug in all_slugs]
                )

    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('INSERT INTO settings (key, value) VALUES (?, ?) '
              'ON CONFLICT(key) DO UPDATE SET value = excluded.value', (key, value))
    conn.commit()
    conn.close()

def get_owner_user_id():
    """The one HA account, if any, designated by an admin as the server
    owner — see is_privileged_user(). Stored in the generic settings
    table rather than a dedicated column since it's a single optional
    value, same reasoning as everything else kept there."""
    return get_setting('owner_user_id') or None

def is_owner(user_id):
    """True for the designated owner only. Deliberately does NOT check
    the admin session here — admin (password) and owner (identity) are
    two independent ways to qualify for the same privileges; callers
    combine them explicitly: `session.get('is_admin') or is_owner(requester_id)`."""
    owner_id = get_owner_user_id()
    return bool(user_id) and bool(owner_id) and user_id == owner_id

DEFAULT_SERVER_NAME = 'Family Home'
DEFAULT_SERVER_ICON = '🏠'

def get_server_identity():
    """The name/icon shown at the top of the channel sidebar — admin-only
    to change, via the admin panel. Falls back to the original hardcoded
    values so a fresh install looks exactly like it always did."""
    return {
        'name': get_setting('server_name') or DEFAULT_SERVER_NAME,
        'icon': get_setting('server_icon') or DEFAULT_SERVER_ICON,
    }

def set_server_identity(name, icon):
    name = (name or '').strip()[:40] or DEFAULT_SERVER_NAME
    icon = (icon or '').strip()[:8] or DEFAULT_SERVER_ICON
    set_setting('server_name', name)
    set_setting('server_icon', icon)

def record_ha_user(user_id, username, display_name):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''INSERT INTO ha_users (user_id, username, display_name, last_seen)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    display_name = excluded.display_name,
                    last_seen = excluded.last_seen''',
              (user_id, username, display_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_known_people():
    """Everyone who's ever opened the chat through Home Assistant, most
    recently seen first. Used for the member sidebar. There's no admin
    roster to maintain — this is just who's actually shown up, using
    each person's chosen alias if they've set one, else their HA display
    name (or username as a fallback)."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT h.user_id, h.display_name, h.username, ua.alias, av.avatar_url
                 FROM ha_users h
                 LEFT JOIN user_aliases ua ON ua.user_id = h.user_id
                 LEFT JOIN user_avatars av ON av.user_id = h.user_id
                 ORDER BY h.last_seen DESC''')
    rows = c.fetchall()
    conn.close()
    seen = set()
    people = []
    for user_id, display_name, username, alias, avatar_url in rows:
        name = (alias or '').strip() or (display_name or '').strip() or (username or '').strip()
        if name and name not in seen:
            seen.add(name)
            people.append({'name': name, 'avatar': avatar_url})
    return people

def get_alias(user_id):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT alias FROM user_aliases WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_alias(user_id, alias):
    alias = (alias or '').strip()[:30]
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    if alias:
        c.execute('''INSERT INTO user_aliases (user_id, alias) VALUES (?, ?)
                     ON CONFLICT(user_id) DO UPDATE SET alias = excluded.alias''',
                  (user_id, alias))
    else:
        # Empty alias = revert to their real Home Assistant name.
        c.execute('DELETE FROM user_aliases WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_avatar(user_id):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT avatar_url FROM user_avatars WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def remove_upload(file_url):
    """Deletes a file this app previously saved under UPLOAD_FOLDER, given
    its public /uploads/... URL. No-ops for anything else (e.g. an
    external GIPHY URL) — and resolves the path to confirm it can't have
    climbed outside the upload folder before deleting anything from disk."""
    if not file_url or not file_url.startswith('/uploads/'):
        return
    candidate = (UPLOAD_FOLDER / file_url[len('/uploads/'):]).resolve()
    if candidate.is_relative_to(UPLOAD_FOLDER.resolve()) and candidate.exists():
        try:
            candidate.unlink()
        except OSError as e:
            logger.warning('Could not remove upload %s: %s', file_url, e)

def set_avatar(user_id, avatar_url):
    old_avatar_url = get_avatar(user_id)
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''INSERT INTO user_avatars (user_id, avatar_url) VALUES (?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET avatar_url = excluded.avatar_url''',
              (user_id, avatar_url))
    conn.commit()
    conn.close()
    if old_avatar_url and old_avatar_url != avatar_url:
        remove_upload(old_avatar_url)

def delete_avatar(user_id):
    old_avatar_url = get_avatar(user_id)
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('DELETE FROM user_avatars WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    remove_upload(old_avatar_url)

def get_known_ha_accounts():
    """Every HA account that's visited, with their real HA name and
    current alias (if any) — used by the admin panel's display-name
    management, which can edit anyone's alias, unlike the self-service
    settings menu which can only edit your own."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT h.user_id, h.display_name, h.username, ua.alias
                 FROM ha_users h
                 LEFT JOIN user_aliases ua ON ua.user_id = h.user_id
                 ORDER BY h.last_seen DESC''')
    rows = c.fetchall()
    conn.close()
    result = []
    for user_id, display_name, username, alias in rows:
        ha_name = (display_name or '').strip() or (username or '').strip() or 'HA User'
        result.append({'user_id': user_id, 'ha_name': ha_name, 'alias': alias or ''})
    return result

def slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '-', text.strip().lower()).strip('-')
    return slug[:30]

def get_categories():
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM channel_categories ORDER BY position ASC')
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1]} for r in rows]

def add_category(name):
    name = name.strip()[:30]
    if not name:
        return None, 'Category name is required.'

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM channel_categories WHERE name = ?', (name,))
    if c.fetchone():
        conn.close()
        return None, 'A category with that name already exists.'
    # New categories land at the end of the list rather than at some
    # arbitrary position — least surprising default, and matches where
    # a newly-added channel lands within its own category below.
    c.execute('SELECT COALESCE(MAX(position), -1) + 1 FROM channel_categories')
    next_position = c.fetchone()[0]
    c.execute('INSERT INTO channel_categories (name, created_at, position) VALUES (?, ?, ?)',
               (name, datetime.now().isoformat(), next_position))
    category_id = c.lastrowid
    conn.commit()
    conn.close()
    return category_id, None

def move_category(category_id, direction):
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return False, 'Invalid category.'
    if direction not in ('up', 'down'):
        return False, 'Invalid direction.'

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT id, position FROM channel_categories ORDER BY position ASC')
    rows = c.fetchall()
    ids = [r[0] for r in rows]
    if category_id not in ids:
        conn.close()
        return False, 'Category not found.'

    idx = ids.index(category_id)
    neighbor_idx = idx - 1 if direction == 'up' else idx + 1
    if neighbor_idx < 0 or neighbor_idx >= len(ids):
        # Already at the top/bottom — the UI disables the button for
        # this case, so reaching it at all means a stale page or a
        # direct API call. Either way, "nothing left to do" isn't
        # really an error, just a harmless no-op.
        conn.close()
        return True, None

    this_id, this_pos = rows[idx]
    neighbor_id, neighbor_pos = rows[neighbor_idx]
    c.execute('UPDATE channel_categories SET position = ? WHERE id = ?', (neighbor_pos, this_id))
    c.execute('UPDATE channel_categories SET position = ? WHERE id = ?', (this_pos, neighbor_id))
    conn.commit()
    conn.close()
    return True, None

def delete_category(category_id):
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return False, 'Invalid category.'

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    # A category with channels still in it can't just vanish — those
    # channels would be left with a category_id pointing at nothing,
    # and the sidebar has no "uncategorized" fallback section to show
    # them in. Move or delete its channels first, same reasoning as
    # "can't delete the last channel" below.
    c.execute('SELECT COUNT(*) FROM channels WHERE category_id = ?', (category_id,))
    if c.fetchone()[0] > 0:
        conn.close()
        return False, "Move or delete this category's channels first."
    c.execute('SELECT COUNT(*) FROM channel_categories')
    if c.fetchone()[0] <= 1:
        conn.close()
        return False, "Can't delete the last remaining category — every channel needs one to belong to."
    c.execute('DELETE FROM channel_categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    return True, None

def get_channels():
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT ch.slug, ch.name, ch.icon, ch.category_id, cc.name
                 FROM channels ch
                 LEFT JOIN channel_categories cc ON cc.id = ch.category_id
                 ORDER BY cc.position ASC, ch.position ASC''')
    rows = c.fetchall()
    conn.close()
    return [{'slug': r[0], 'name': r[1], 'icon': r[2], 'category_id': r[3], 'category_name': r[4]} for r in rows]

def add_channel(name, icon, category_id):
    name = name.strip()[:30]
    icon = (icon.strip() or '#')[:8]
    slug = slugify(name)
    if not name or not slug:
        return None, 'Channel name is required.'

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()

    # A channel always belongs to a real category — admins create
    # categories, everyone else picks from what already exists.
    # Validated here against the actual table, not just trusted from
    # whatever the client's dropdown happened to submit.
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        conn.close()
        return None, 'Choose a category for this channel.'
    c.execute('SELECT 1 FROM channel_categories WHERE id = ?', (category_id,))
    if not c.fetchone():
        conn.close()
        return None, 'Choose a valid category.'

    c.execute('SELECT 1 FROM channels WHERE slug = ?', (slug,))
    if c.fetchone():
        conn.close()
        return None, 'A channel with that name already exists.'
    # Position is scoped within the category (see move_channel()) — a
    # freshly-added channel lands at the end of its own category's
    # list, not the end of some single global ordering.
    c.execute('SELECT COALESCE(MAX(position), -1) + 1 FROM channels WHERE category_id = ?', (category_id,))
    next_position = c.fetchone()[0]
    c.execute('INSERT INTO channels (slug, name, icon, category_id, position) VALUES (?, ?, ?, ?, ?)',
               (slug, name, icon, category_id, next_position))
    conn.commit()
    conn.close()
    return slug, None

def move_channel(slug, direction):
    if direction not in ('up', 'down'):
        return False, 'Invalid direction.'

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT id, category_id FROM channels WHERE slug = ?', (slug,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, 'Channel not found.'
    this_channel_id, category_id = row

    # Scoped to siblings within the same category — a channel only ever
    # moves relative to the others in its own category, never across
    # categories (moving a channel to a *different* category is a
    # separate, unrelated action this doesn't attempt).
    c.execute('SELECT id, position FROM channels WHERE category_id = ? ORDER BY position ASC', (category_id,))
    rows = c.fetchall()
    ids = [r[0] for r in rows]
    idx = ids.index(this_channel_id)
    neighbor_idx = idx - 1 if direction == 'up' else idx + 1
    if neighbor_idx < 0 or neighbor_idx >= len(ids):
        conn.close()
        return True, None

    this_id, this_pos = rows[idx]
    neighbor_id, neighbor_pos = rows[neighbor_idx]
    c.execute('UPDATE channels SET position = ? WHERE id = ?', (neighbor_pos, this_id))
    c.execute('UPDATE channels SET position = ? WHERE id = ?', (this_pos, neighbor_id))
    conn.commit()
    conn.close()
    return True, None

def delete_channel(slug):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM channels')
    if c.fetchone()[0] <= 1:
        conn.close()
        return False, "Can't delete the last remaining channel."
    c.execute('DELETE FROM channels WHERE slug = ?', (slug,))
    conn.commit()
    conn.close()
    # Messages already posted in this channel are left in place (just no
    # longer reachable from the channel list) rather than deleted, so
    # re-creating a channel with the same slug would bring them back.
    return True, None

def get_messages(limit=100, channel='general'):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT m.*, ua.alias as current_alias, av.avatar_url
                 FROM messages m
                 LEFT JOIN user_aliases ua ON ua.user_id = m.sender_id
                 LEFT JOIN user_avatars av ON av.user_id = m.sender_id
                 WHERE m.channel = ?
                 ORDER BY m.timestamp DESC LIMIT ?''', (channel, limit))
    messages = c.fetchall()

    # Get columns
    columns = [description[0] for description in c.description]
    result = []
    message_ids = []
    for row in messages:
        msg = dict(zip(columns, row))
        # If the sender has since set (or been given) an alias, show that
        # instead of whatever name was frozen into the message at send
        # time — this is what makes a rename apply retroactively.
        if msg.get('current_alias'):
            msg['sender'] = msg['current_alias']
        del msg['current_alias']
        msg['reactions'] = {}
        result.append(msg)
        message_ids.append(msg['id'])

    # Reactions used to be folded into the message query with
    # GROUP_CONCAT(r.emoji || ':' || r.user), then unpacked client-side by
    # splitting on ':' and ','. That broke as soon as either value could
    # contain those characters — a reaction using a *custom* emoji is
    # stored as ":name:", which already contains colons, so splitting on
    # ':' produced an empty emoji and a mangled username (visible as a
    # reaction pill showing just a bare count with no emoji). Fetching
    # reactions as a separate, plain query and assembling them here in
    # Python sidesteps the whole class of delimiter-collision bugs,
    # regardless of what characters end up in an emoji name or username.
    if message_ids:
        placeholders = ','.join('?' * len(message_ids))
        c.execute(f'SELECT message_id, emoji, user FROM reactions WHERE message_id IN ({placeholders})',
                  message_ids)
        reactions_by_message = {}
        for message_id, emoji, user in c.fetchall():
            reactions_by_message.setdefault(message_id, {}).setdefault(emoji, []).append(user)
        for msg in result:
            msg['reactions'] = reactions_by_message.get(msg['id'], {})

    conn.close()
    return list(reversed(result))

def save_message(sender, content, channel='general', msg_type='text', 
                 file_url=None, file_name=None, file_size=None, mime_type=None,
                 sender_id=None):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('''INSERT INTO messages 
                 (sender, content, timestamp, channel, message_type, 
                  file_url, file_name, file_size, mime_type, sender_id) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (sender, content, timestamp, channel, msg_type,
               file_url, file_name, file_size, mime_type, sender_id))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def delete_message(message_id, requester_id, can_manage):
    """Regular users can only delete their own messages (matched by the
    stable sender_id, not the display name — a renamed or reused alias
    shouldn't matter here). An admin (password session) or the
    designated owner (identity-based, see is_owner()) can delete
    anyone's — can_manage covers both, decided by the caller. Returns
    (channel, error); channel tells the caller which socket room to
    notify."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT sender_id, channel, file_url FROM messages WHERE id = ?', (message_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, 'Message not found — it may have already been deleted.'

    sender_id, channel, file_url = row
    if not can_manage and sender_id != requester_id:
        conn.close()
        return None, 'You can only delete your own messages.'

    c.execute('DELETE FROM reactions WHERE message_id = ?', (message_id,))
    c.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()

    remove_upload(file_url)
    return channel, None

def get_custom_emojis():
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT name, file_path FROM custom_emojis')
    emojis = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return emojis

def save_custom_emoji(name, file_path, created_by):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    try:
        c.execute('INSERT INTO custom_emojis (name, file_path, created_by, created_at) VALUES (?, ?, ?, ?)',
                  (name, file_path, created_by, timestamp))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def ingress_redirect(path):
    """Home Assistant ingress serves this add-on under a dynamic prefix
    (e.g. /api/hassio_ingress/<token>) that's stripped before the request
    reaches this container. A plain redirect() to a root-relative path like
    "/admin" loses that prefix, so the browser ends up requesting "/admin"
    at the Home Assistant domain root instead -> 404. Ingress forwards the
    original prefix via the X-Ingress-Path header so we can rebuild the
    correct absolute URL. If the header is missing (e.g. direct, non-ingress
    access) or looks malformed, fall back to the plain path.

    The validation below is stricter than it looks like it needs to be:
    a prefix has to be a plain relative path, nothing else. The previous
    version only checked for a leading '/' and rejected ':', which
    blocks "http://evil.com" but not "//evil.com" — browsers treat a
    Location starting with "//" as a protocol-relative URL pointing at
    a different host entirely, using whatever scheme the current page
    loaded over. That string starts with '/' and contains no ':', so it
    sailed straight through the old check. Backslashes are normalized
    first too, since browsers commonly treat them as equivalent to
    forward slashes in a URL even though Python's urlparse does not —
    "/\\evil.com" wouldn't otherwise be recognized as the "//evil.com"
    it becomes once a browser gets hold of it.
    """
    prefix = request.headers.get('X-Ingress-Path', '').replace('\\', '/')
    parsed_prefix = urllib.parse.urlparse(prefix)
    prefix_is_valid = (prefix.startswith('/') and not prefix.startswith('//')
                        and not parsed_prefix.netloc and not parsed_prefix.scheme)

    # path is always a server-generated route (url_for(...)) in every
    # current caller, never user input — but validating it the same way
    # as prefix is what actually makes that a property of every caller,
    # not just an accident of how the function happens to be used
    # today. A future caller passing anything client-influenced here
    # would otherwise reopen the exact issue prefix's own validation
    # exists to close.
    safe_path = (path or '').replace('\\', '/')
    parsed_path = urllib.parse.urlparse(safe_path)
    path_is_valid = (safe_path.startswith('/') and not safe_path.startswith('//')
                      and not parsed_path.netloc and not parsed_path.scheme)

    # Every branch below either uses a value that just passed its own
    # validation check immediately above, or a hardcoded literal —
    # never a variable that was conditionally reassigned earlier and
    # then used further down. Behaviorally this is identical to
    # reassigning each tainted value to a safe fallback and making one
    # call at the end (which is what this function used to do), but
    # written this way instead because CodeQL's static analysis
    # reliably recognizes "redirect() called on a value that just
    # passed an explicit if-check in the same branch" as sanitized,
    # and did not reliably recognize the reassignment-based version —
    # it kept flagging this line even after prefix and safe_path were
    # both being fully validated.
    if prefix_is_valid and path_is_valid:
        return redirect(prefix + safe_path)
    if path_is_valid:
        return redirect(safe_path)
    if prefix_is_valid:
        return redirect(prefix + '/')
    return redirect('/')

@app.after_request
def set_cache_headers(response):
    # Every response from this add-on is either the live document itself
    # or something that can change from one moment to the next (a
    # message list, a script that just got updated, an uploaded file
    # that could theoretically be re-uploaded under the same name after
    # a delete) — none of it should ever be served from a cache.
    #
    # This used to be narrower: only /static/ got a header at all (just
    # "no-cache", which still permits caching *with* revalidation), and
    # the main document (index.html, served from "/") got nothing.
    # That gap is a real bug, not just theoretical — it's the second
    # time a "stale content through Home Assistant's ingress iframe,
    # only a hard refresh fixes it" report has come up in this app's
    # history (the first was the GIF button not appearing after it
    # shipped). Whatever's happening in that iframe layer isn't reliably
    # honoring "no-cache" revalidation, so this goes with the strictly
    # stronger "no-store" — never keep a copy at all, anywhere, full
    # stop — rather than continuing to rely on revalidation working
    # correctly through a proxy layer we don't control. The performance
    # cost of that (every asset re-downloaded in full on every load,
    # rather than a cheap conditional GET) is negligible at this app's
    # scale and is a small price for actually eliminating the bug class.
    response.headers['Cache-Control'] = 'no-store'
    return response

def resolve_ha_identity():
    """The chat name is the logged-in Home Assistant user's own chosen
    alias if they've set one (via the settings menu, or set for them by
    an admin), otherwise their HA display name, otherwise their login
    username. Returns (ha_user_id, chat_name); chat_name is None only if
    there's no HA identity at all (e.g. accessed outside ingress)."""
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return None, None
    alias = get_alias(ha_user_id)
    if alias:
        return ha_user_id, alias
    display_name = request.headers.get('X-Remote-User-Display-Name', '').strip()
    username = request.headers.get('X-Remote-User-Name', '').strip()
    chat_name = (display_name or username or 'HA User')[:30]
    return ha_user_id, chat_name

def require_admin(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('is_admin'):
            return ingress_redirect(url_for('admin_panel'))
        return view(*args, **kwargs)
    return wrapped

@app.errorhandler(413)
def handle_too_large(e):
    # Without this, an over-limit upload gets Werkzeug's default HTML
    # error page instead of the JSON the upload UI actually knows how to
    # show as an error message.
    limit_mb = MAX_FILE_SIZE // (1024 * 1024)
    return jsonify({'error': f'File is too large — the limit is {limit_mb}MB.'}), 413

@app.errorhandler(Exception)
def handle_uncaught_exception(e):
    logger.exception('Unhandled exception on %s %s', request.method, request.path)
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error — check the add-on log for details.'}), 500
    return 'Internal server error — check the add-on log for details.', 500

@app.route('/')
def index():
    # Home Assistant's ingress proxy adds these headers identifying the
    # logged-in HA user. They're only present when accessed through
    # ingress (sidebar/panel), and X-Remote-User-Name specifically isn't
    # guaranteed for every auth provider (e.g. command-line/OIDC) — so we
    # key off the more reliable X-Remote-User-Id and treat everything as
    # optional.
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if ha_user_id:
        ha_username = request.headers.get('X-Remote-User-Name', '')
        ha_display_name = request.headers.get('X-Remote-User-Display-Name', '')
        record_ha_user(ha_user_id, ha_username, ha_display_name)
    auto_user_id, auto_user = resolve_ha_identity()
    server_identity = get_server_identity()

    # Fresh on every single page load, not just once per container
    # restart — see the comment where this used to be a module-level
    # constant, above, for why a once-per-restart version wasn't
    # aggressive enough to reliably defeat Home Assistant's ingress
    # caching behavior.
    asset_version = secrets.token_hex(8)

    return render_template('index.html',
                          members=get_known_people(),
                          theme=THEME,
                          asset_version=asset_version,
                          inline_css=INLINE_CSS,
                          channels=get_channels(),
                          categories=get_categories(),
                          auto_user=auto_user,
                          auto_user_id=auto_user_id,
                          auto_avatar=get_avatar(auto_user_id) if auto_user_id else None,
                          is_admin=bool(session.get('is_admin')),
                          is_owner=is_owner(auto_user_id),
                          server_name=server_identity['name'],
                          server_icon=server_identity['icon'],
                          giphy_enabled=bool(GIPHY_API_KEY),
                          calendar_enabled=bool(SUPERVISOR_TOKEN))

@app.route('/api/channels')
def api_channels():
    return jsonify(get_channels())

@app.route('/api/categories')
def api_categories():
    return jsonify(get_categories())

@app.route('/api/channels/add', methods=['POST'])
def api_add_channel():
    # Adding a channel is self-service for any signed-in family member.
    # Deleting one is more disruptive (affects everyone, drops it out of
    # the sidebar for the whole family at once) — see api_delete_channel
    # below for who's allowed to do that. Categories are the other way
    # around: only an admin can create one (see admin_add_category),
    # but anyone can add a channel into one that already exists.
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    data = request.get_json(silent=True) or {}
    slug, error = add_channel(data.get('name', ''), data.get('icon', '#'), data.get('category_id'))
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'slug': slug, 'channels': get_channels()})

@app.route('/api/channels/delete', methods=['POST'])
def api_delete_channel():
    # Self-service for the designated owner or an authenticated admin
    # session — anyone else still has to go through /admin (i.e.
    # doesn't have this capability at all without the admin password).
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not (bool(session.get('is_admin')) or is_owner(ha_user_id)):
        return jsonify({'error': 'Only the server owner or an admin can delete channels.'}), 403
    data = request.get_json(silent=True) or {}
    ok, error = delete_channel(data.get('slug', ''))
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'channels': get_channels()})

@app.route('/api/channels/move', methods=['POST'])
def api_move_channel():
    # Reordering is owner-or-admin, same as deleting — unlike creating a
    # category (admin only, see admin_add_category), this only ever
    # rearranges what's already there rather than adding something new,
    # so it's granted the same way channel deletion already is.
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not (bool(session.get('is_admin')) or is_owner(ha_user_id)):
        return jsonify({'error': 'Only the server owner or an admin can reorder channels.'}), 403
    data = request.get_json(silent=True) or {}
    ok, error = move_channel(data.get('slug', ''), data.get('direction', ''))
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'channels': get_channels()})

@app.route('/api/categories/move', methods=['POST'])
def api_move_category():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not (bool(session.get('is_admin')) or is_owner(ha_user_id)):
        return jsonify({'error': 'Only the server owner or an admin can reorder categories.'}), 403
    data = request.get_json(silent=True) or {}
    ok, error = move_category(data.get('category_id', ''), data.get('direction', ''))
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'categories': get_categories(), 'channels': get_channels()})

def _escape_like(s):
    # LIKE treats % and _ as wildcards — escape them so a search for a
    # literal "50%" or "file_name" doesn't behave unexpectedly.
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT m.id, m.sender, m.content, m.timestamp, m.channel,
                        ua.alias as current_alias, m.message_type
                 FROM messages m
                 LEFT JOIN user_aliases ua ON ua.user_id = m.sender_id
                 WHERE m.content LIKE ? ESCAPE '\\'
                 ORDER BY m.timestamp DESC LIMIT 50''',
              (f'%{_escape_like(query)}%',))
    rows = c.fetchall()
    conn.close()

    channels_by_slug = {ch['slug']: ch for ch in get_channels()}
    results = []
    for msg_id, sender, content, timestamp, channel, alias, message_type in rows:
        ch = channels_by_slug.get(channel)
        # content is a JSON payload for calendar_event messages, not
        # display text (see api_create_calendar_event()) — would
        # otherwise show as raw JSON in search results.
        display_content = summarize_message_for_notification(content, message_type, None) if message_type == 'calendar_event' else content
        results.append({
            'id': msg_id,
            'sender': alias or sender,
            'content': display_content,
            'timestamp': timestamp,
            'channel': channel,
            'channel_name': ch['name'] if ch else channel,
            'channel_icon': ch['icon'] if ch else '#',
        })
    return jsonify(results)

@app.route('/api/files')
def api_files():
    channel = request.args.get('channel', 'general')
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT m.id, m.sender, m.file_url, m.file_name, m.file_size, m.mime_type, m.timestamp,
                        ua.alias as current_alias
                 FROM messages m
                 LEFT JOIN user_aliases ua ON ua.user_id = m.sender_id
                 WHERE m.channel = ? AND m.file_url IS NOT NULL
                 ORDER BY m.timestamp DESC LIMIT 100''', (channel,))
    rows = c.fetchall()
    conn.close()

    results = []
    for msg_id, sender, file_url, file_name, file_size, mime_type, timestamp, alias in rows:
        results.append({
            'id': msg_id,
            'sender': alias or sender,
            'url': file_url,
            'filename': file_name,
            'size': file_size,
            'mime_type': mime_type,
            'timestamp': timestamp,
        })
    return jsonify(results)

@app.route('/api/me')
def api_me():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    display_name = request.headers.get('X-Remote-User-Display-Name', '').strip()
    username = request.headers.get('X-Remote-User-Name', '').strip()
    ha_name = display_name or username or 'HA User'
    return jsonify({
        'ha_name': ha_name,
        'alias': get_alias(ha_user_id) or '',
        'avatar_url': get_avatar(ha_user_id) or '',
    })

@app.route('/api/my-alias', methods=['POST'])
def api_set_my_alias():
    # The target is always the requester's own HA user ID, derived from
    # the ingress headers — never from anything in the request body — so
    # this endpoint can only ever change your own alias, not someone
    # else's. Changing anyone else's is admin-only (see /admin/aliases).
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    data = request.get_json(silent=True) or {}
    set_alias(ha_user_id, data.get('alias', ''))
    return jsonify({'success': True})

@app.route('/api/my-avatar', methods=['POST'])
def api_set_my_avatar():
    # Same shape as /api/my-alias: the target is always the requester's
    # own HA user ID from the ingress headers, never taken from the
    # request body, so this can only ever change your own avatar.
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No image selected'}), 400

    file = request.files['file']
    # Deliberately not derived from file.filename — a client-supplied
    # filename is exactly the kind of untrusted input that shouldn't
    # flow into a path expression at all, extension or otherwise (this
    # reverted once already after being fixed; see CHANGELOG). Only the
    # declared mimetype, checked against a fixed server-side mapping,
    # ever decides the saved extension — an "evil.exe" upload with a
    # declared image/png mimetype saves as .png, never .exe, because
    # nothing about the filename itself is ever used here.
    mime_to_ext = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/gif': 'gif',
        'image/webp': 'webp',
    }
    ext = mime_to_ext.get((file.mimetype or '').lower(), '')
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        return jsonify({'error': 'Avatar must be a PNG, JPG, GIF, or WEBP image.'}), 400

    # Namespaced by the requester's own HA user ID (not client-supplied)
    # and timestamped, same collision-avoidance approach as /api/upload —
    # this is what makes a fresh upload actually replace the old avatar
    # everywhere it's shown, rather than getting cached under an
    # already-seen filename.
    safe_id = secure_filename(ha_user_id) or 'user'
    filename = f"avatar_{safe_id}_{int(datetime.now().timestamp())}.{ext}"
    file.save(UPLOAD_FOLDER / filename)
    avatar_url = f'/uploads/{filename}'
    set_avatar(ha_user_id, avatar_url)
    return jsonify({'success': True, 'avatar_url': avatar_url})

@app.route('/api/my-avatar', methods=['DELETE'])
def api_delete_my_avatar():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    delete_avatar(ha_user_id)
    return jsonify({'success': True})

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return render_template('admin.html', logged_in=False, error=request.args.get('error'))

    all_calendars, calendar_error = get_calendar_entities()
    allowed_ids = get_allowed_calendar_ids()
    calendars_with_state = []
    if all_calendars:
        for cal in all_calendars:
            # Unset (allowed_ids is None) means nothing's ever been
            # restricted — every calendar shows as checked by default,
            # communicating "everything is currently allowed" rather
            # than starting from an unexplained blank slate.
            checked = allowed_ids is None or cal['entity_id'] in allowed_ids
            calendars_with_state.append({**cal, 'checked': checked})

    return render_template('admin.html', logged_in=True,
                          saved=request.args.get('saved'),
                          active_tab=request.args.get('tab', 'chatname'),
                          channels=get_channels(),
                          categories=get_categories(),
                          channel_error=request.args.get('channel_error'),
                          ha_accounts=get_known_ha_accounts(),
                          current_owner_id=get_owner_user_id(),
                          server_identity=get_server_identity(),
                          all_calendars=calendars_with_state,
                          calendar_error=calendar_error)

@app.route('/admin/calendars/set', methods=['POST'])
@require_admin
def admin_set_calendars():
    # A checkbox that's unchecked simply doesn't appear in the submitted
    # form data at all — getlist() only returns the ones that were
    # checked, which is exactly the allowed set.
    allowed = request.form.getlist('allowed_calendars')
    set_allowed_calendars(allowed)
    return ingress_redirect(url_for('admin_panel', saved='1', tab='calendars'))

@app.route('/admin/server-name/set', methods=['POST'])
@require_admin
def admin_set_server_name():
    set_server_identity(request.form.get('server_name', ''), request.form.get('server_icon', ''))
    return ingress_redirect(url_for('admin_panel', saved='1', tab='chatname'))

@app.route('/admin/owner/set', methods=['POST'])
@require_admin
def admin_set_owner():
    # Empty selection clears the owner entirely — set_setting stores ''
    # rather than deleting the row, which get_owner_user_id() already
    # treats as "no owner" via `or None`.
    owner_user_id = request.form.get('owner_user_id', '').strip()
    set_setting('owner_user_id', owner_user_id)
    return ingress_redirect(url_for('admin_panel', saved='1', tab='owner'))

@app.route('/admin/login', methods=['POST'])
def admin_login():
    if _admin_login_rate_limited():
        logger.warning('Admin login blocked — too many recent failed attempts.')
        return ingress_redirect(url_for('admin_panel', error='Too many failed attempts. Try again in a few minutes.'))

    password = request.form.get('password', '')
    # Constant-time-safe comparison via check_password_hash (hmac.compare_digest internally)
    if check_password_hash(ADMIN_PASSWORD_HASH, password):
        _admin_login_failures.clear()
        session['is_admin'] = True
        return ingress_redirect(url_for('admin_panel'))

    _admin_login_failures.append(datetime.now().timestamp())
    logger.warning('Failed admin login attempt (%d in the last %d minutes)',
                    len(_admin_login_failures), _ADMIN_LOGIN_WINDOW_SECONDS // 60)
    return ingress_redirect(url_for('admin_panel', error='Incorrect password'))

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return ingress_redirect(url_for('index'))

@app.route('/admin/channels/delete', methods=['POST'])
@require_admin
def admin_delete_channel():
    slug = request.form.get('slug', '')
    ok, error = delete_channel(slug)
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error, tab='channels'))
    return ingress_redirect(url_for('admin_panel', saved='1', tab='channels'))

@app.route('/admin/channels/move', methods=['POST'])
@require_admin
def admin_move_channel():
    ok, error = move_channel(request.form.get('slug', ''), request.form.get('direction', ''))
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error, tab='channels'))
    return ingress_redirect(url_for('admin_panel', saved='1', tab='channels'))

@app.route('/admin/categories/add', methods=['POST'])
@require_admin
def admin_add_category():
    category_id, error = add_category(request.form.get('name', ''))
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error, tab='channels'))
    return ingress_redirect(url_for('admin_panel', saved='1', tab='channels'))

@app.route('/admin/categories/move', methods=['POST'])
@require_admin
def admin_move_category():
    ok, error = move_category(request.form.get('category_id', ''), request.form.get('direction', ''))
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error, tab='channels'))
    return ingress_redirect(url_for('admin_panel', saved='1', tab='channels'))

@app.route('/admin/categories/delete', methods=['POST'])
@require_admin
def admin_delete_category():
    ok, error = delete_category(request.form.get('category_id', ''))
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error, tab='channels'))
    return ingress_redirect(url_for('admin_panel', saved='1', tab='channels'))

@app.route('/admin/aliases', methods=['POST'])
@require_admin
def admin_update_aliases():
    # Unlike /api/my-alias, this can target any known HA account — that's
    # what makes it admin-only. Each field is named alias_<user_id> so one
    # form submission can update everyone at once.
    for field, value in request.form.items():
        if not field.startswith('alias_'):
            continue
        user_id = field[len('alias_'):]
        set_alias(user_id, value)
    return ingress_redirect(url_for('admin_panel', saved='1', tab='aliases'))

@app.route('/api/messages')
def get_messages_api():
    channel = request.args.get('channel', 'general')
    return jsonify(get_messages(channel=channel))

@app.route('/api/emojis')
def get_emojis():
    return jsonify(get_custom_emojis())

@app.route('/api/upload', methods=['POST'])
def upload_file():
    # Every other state-changing route in this app independently checks
    # for a resolvable Home Assistant identity rather than relying
    # solely on "well, ingress gates the whole app anyway" — this route
    # was the one exception. Being consistent about it is cheap and
    # means this route degrades the same way the rest of the app does if
    # that outer assumption (no direct port exposure — see config.yaml)
    # were ever accidentally changed.
    if not request.headers.get('X-Remote-User-Id'):
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to prevent collisions
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
        
        file_path = UPLOAD_FOLDER / filename
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        mime_type = file.content_type
        
        return jsonify({
            'success': True,
            'url': f'/uploads/{filename}',
            'filename': filename,
            'size': file_size,
            'mime_type': mime_type
        })
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/emoji/upload', methods=['POST'])
def upload_emoji():
    if not request.headers.get('X-Remote-User-Id'):
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    if 'file' not in request.files or 'name' not in request.form:
        return jsonify({'error': 'Missing file or name'}), 400
    
    file = request.files['file']
    name = request.form['name'].strip().replace(':', '')
    _, created_by = resolve_ha_identity()
    created_by = created_by or 'unknown'
    
    if not name or file.filename == '':
        return jsonify({'error': 'Invalid name or file'}), 400
    
    # Only allow images for emojis
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        return jsonify({'error': 'Only images allowed for emojis'}), 400
    
    # `name` is client-supplied and was, until now, dropped straight into
    # the filename with no sanitization beyond stripping ':' — the emoji_
    # prefix happens to make this not currently exploitable as a path
    # traversal (the OS requires each intermediate directory in a '../'
    # chain to actually exist, which "emoji_<garbage>" never does), but
    # relying on that is fragile and inconsistent with /api/upload, which
    # correctly uses secure_filename(). This closes it properly instead
    # of depending on that OS behavior remaining true.
    safe_name = secure_filename(name) or 'emoji'
    filename = f"emoji_{safe_name}_{int(datetime.now().timestamp())}.{ext}"
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)
    
    if save_custom_emoji(f':{name}:', f'/uploads/{filename}', created_by):
        return jsonify({'success': True, 'name': f':{name}:', 'url': f'/uploads/{filename}'})
    else:
        os.remove(file_path)
        return jsonify({'error': 'Emoji name already exists'}), 400

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

GIPHY_API_BASE = 'https://api.giphy.com/v1/gifs'

def _clamp_int(value, default, minimum, maximum):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))

def giphy_get(path, params):
    """Proxy a request to the GIPHY API and shape the result down to what
    the picker needs. The API key is attached here, server-side, so it's
    never exposed to the browser — the client only ever calls our own
    /api/giphy/* routes."""
    if not GIPHY_API_KEY:
        return None, 'GIPHY is not configured. Add a GIPHY API key in the add-on configuration.'

    query = dict(params)
    query['api_key'] = GIPHY_API_KEY
    url = f'{GIPHY_API_BASE}/{path}?{urllib.parse.urlencode(query)}'

    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        logger.warning('GIPHY API returned HTTP %s for %s', e.code, path)
        if e.code in (401, 403):
            return None, 'GIPHY rejected the configured API key.'
        return None, 'GIPHY request failed.'
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning('GIPHY API unreachable: %s', e)
        return None, 'Could not reach GIPHY — try again in a moment.'
    except json.JSONDecodeError as e:
        logger.warning('GIPHY API returned unparseable data: %s', e)
        return None, 'GIPHY returned an unexpected response.'

    gifs = []
    for item in payload.get('data', []):
        images = item.get('images', {})
        original = images.get('original', {})
        preview = images.get('fixed_width_small') or images.get('preview_gif') or original
        if not original.get('url'):
            continue
        gifs.append({
            'id': item.get('id'),
            'title': (item.get('title') or 'GIF')[:100],
            'url': original.get('url'),
            'preview_url': preview.get('url') or original.get('url'),
            'width': _clamp_int(original.get('width'), 0, 0, 10000),
            'height': _clamp_int(original.get('height'), 0, 0, 10000),
        })
    return gifs, None

@app.route('/api/giphy/trending')
def giphy_trending():
    limit = _clamp_int(request.args.get('limit'), 24, 1, 50)
    offset = _clamp_int(request.args.get('offset'), 0, 0, 4999)
    gifs, error = giphy_get('trending', {'limit': limit, 'offset': offset, 'rating': 'pg-13'})
    if error:
        return jsonify({'error': error}), 503
    return jsonify({'gifs': gifs})

@app.route('/api/giphy/search')
def giphy_search():
    q = request.args.get('q', '').strip()
    if not q:
        return giphy_trending()
    limit = _clamp_int(request.args.get('limit'), 24, 1, 50)
    offset = _clamp_int(request.args.get('offset'), 0, 0, 4999)
    gifs, error = giphy_get('search', {'q': q, 'limit': limit, 'offset': offset, 'rating': 'pg-13'})
    if error:
        return jsonify({'error': error}), 503
    return jsonify({'gifs': gifs})

# --- Home Assistant notifications ---
# Push delivery is entirely Home Assistant's own (via the HA Companion
# App's notify.* services, e.g. notify.mobile_app_johns_iphone) — this
# add-on just decides whether and where to call one when a message comes
# in. Requests go through the supervisor's Home Assistant API proxy
# rather than a direct connection, authenticated with the token the
# supervisor injects automatically once `homeassistant_api: true` is set.
HA_API_BASE = 'http://supervisor/core/api'

def ha_api_request(method, path, json_body=None, timeout=5):
    """Proxy a request to Home Assistant's core REST API. Returns
    (data, error) — data is None on any failure, with error set to a
    message safe to show the person (never the token or raw exception)."""
    if not SUPERVISOR_TOKEN:
        return None, 'This add-on was not built with Home Assistant API access — add "homeassistant_api: true" to its configuration and rebuild it.'

    url = f'{HA_API_BASE}{path}'
    headers = {
        'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
        'Content-Type': 'application/json',
    }
    data = json.dumps(json_body).encode('utf-8') if json_body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return (json.loads(body) if body else {}), None
    except urllib.error.HTTPError as e:
        logger.warning('Home Assistant API returned HTTP %s for %s %s', e.code, method, path)
        if e.code in (401, 403):
            return None, 'Home Assistant rejected this request — the add-on may need to be rebuilt after enabling API access.'
        return None, 'Home Assistant returned an error for that request.'
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning('Home Assistant API unreachable: %s', e)
        return None, 'Could not reach Home Assistant.'
    except json.JSONDecodeError as e:
        logger.warning('Home Assistant API returned unparseable data: %s', e)
        return None, 'Home Assistant returned an unexpected response.'

def send_ha_notification(notify_service, title, message):
    """Calls notify.<service> in Home Assistant. notify_service may be
    given with or without the "notify." prefix. Returns (ok, error)."""
    service = (notify_service or '').strip()
    if service.startswith('notify.'):
        service = service[len('notify.'):]
    if not service:
        return False, 'No device selected.'
    # notify_service ultimately comes from client-supplied JSON (see
    # api_set_notify_prefs/api_notify_test below) and gets interpolated
    # straight into the path of a privileged, server-side request to
    # Home Assistant's own API — one made with this add-on's Supervisor
    # token, not the requesting person's own credentials. Without this,
    # a value like "../../states" or "../homeassistant/restart" would be
    # sent as part of that URL essentially unvalidated; whether it can
    # actually escape the /services/notify/ prefix depends on internals
    # of Supervisor's own request routing that this add-on has no
    # control over and shouldn't have to trust. A strict allowlist here
    # closes that off entirely regardless of how that routing behaves —
    # real HA service/entity name segments are only ever lowercase
    # letters, digits, and underscores, so anything else is rejected
    # outright rather than attempting to sanitize it.
    if not re.fullmatch(r'[a-zA-Z0-9_]+', service):
        return False, 'Invalid device.'
    _, error = ha_api_request('POST', f'/services/notify/{service}',
                               {'title': title, 'message': message})
    return (error is None), error

def get_notify_service(user_id):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT notify_service FROM notification_prefs WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return (row[0] if row else '') or ''

def set_notify_service(user_id, notify_service):
    notify_service = (notify_service or '').strip()[:100]
    # Same allowlist as send_ha_notification, enforced here too so an
    # invalid value can't even be saved in the first place — this isn't
    # purely redundant with the check at call time: rejecting early
    # gives the person an immediate, specific error instead of a
    # notification that silently never arrives.
    if notify_service and not re.fullmatch(r'(notify\.)?[a-zA-Z0-9_]+', notify_service):
        notify_service = ''
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''INSERT INTO notification_prefs (user_id, enabled, notify_service) VALUES (?, 0, ?)
                 ON CONFLICT(user_id) DO UPDATE SET notify_service = excluded.notify_service''',
              (user_id, notify_service))
    conn.commit()
    conn.close()

def get_subscribed_channels(user_id):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT channel FROM notification_channel_subs WHERE user_id = ?', (user_id,))
    channels = [row[0] for row in c.fetchall()]
    conn.close()
    return channels

def set_subscribed_channels(user_id, channels):
    # Silently drop anything that isn't a real channel slug, rather than
    # erroring — the request body is client-supplied, and a stale channel
    # (deleted since the page loaded) shouldn't block saving the rest.
    valid_slugs = {ch['slug'] for ch in get_channels()}
    channels = [ch for ch in (channels or []) if ch in valid_slugs]
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('DELETE FROM notification_channel_subs WHERE user_id = ?', (user_id,))
    if channels:
        c.executemany('INSERT INTO notification_channel_subs (user_id, channel) VALUES (?, ?)',
                       [(user_id, ch) for ch in channels])
    conn.commit()
    conn.close()

def get_subscribers_for_channel(channel, exclude_user_id=None):
    """(user_id, notify_service) for everyone subscribed to this specific
    channel who's also picked a device — excluding the given user, since
    a sender shouldn't be notified about their own message."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT s.user_id, p.notify_service
                 FROM notification_channel_subs s
                 JOIN notification_prefs p ON p.user_id = s.user_id
                 WHERE s.channel = ?''', (channel,))
    rows = c.fetchall()
    conn.close()
    return [(uid, svc) for uid, svc in rows if svc and uid != exclude_user_id]

def summarize_message_for_notification(content, msg_type, file_info):
    if msg_type == 'calendar_event':
        # content is a JSON payload here, not display text (see
        # api_create_calendar_event()) — has to be handled before the
        # generic `if content:` branch below, which would otherwise just
        # return the raw JSON as the notification body.
        try:
            event = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return 'Added a calendar event'
        when = event.get('start', '')
        if event.get('all_day') and when:
            try:
                when = datetime.strptime(when, '%Y-%m-%d').strftime('%a, %b %-d')
            except ValueError:
                pass
        elif when:
            try:
                when = datetime.strptime(when, '%Y-%m-%d %H:%M:%S').strftime('%a, %b %-d · %-I:%M %p')
            except ValueError:
                pass
        title = event.get('title', 'Untitled event')
        return f'📅 Added: {title} — {when}' if when else f'📅 Added: {title}'
    content = (content or '').strip()
    if content:
        return content if len(content) <= 200 else content[:197] + '…'
    if msg_type == 'gif':
        return 'Sent a GIF'
    if msg_type == 'image':
        return 'Sent a photo'
    if msg_type == 'video':
        return 'Sent a video'
    if msg_type == 'file':
        name = (file_info or {}).get('filename')
        return f'Shared {name}' if name else 'Shared a file'
    return 'Sent a message'

def get_mentionable_users():
    """(user_id, name) for everyone who's ever opened the chat, using the
    exact same canonical name (alias, else HA display name, else
    username) get_known_people() shows in the member list — so a
    mention always matches what's actually displayed on screen, not
    some other identity string the person typing it would have no way
    to know. Unlike get_known_people(), this keeps user_id (needed to
    actually notify someone) rather than deduping purely by name."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT h.user_id, h.display_name, h.username, ua.alias
                 FROM ha_users h
                 LEFT JOIN user_aliases ua ON ua.user_id = h.user_id''')
    rows = c.fetchall()
    conn.close()
    people = []
    for user_id, display_name, username, alias in rows:
        name = (alias or '').strip() or (display_name or '').strip() or (username or '').strip()
        if name:
            people.append({'user_id': user_id, 'name': name})
    return people

def find_mentioned_user_ids(content, exclude_user_id=None):
    """Which known people got @mentioned in a message — matched by exact
    name (longest first, so "@John Smith" matches the whole thing rather
    than just "@John" if both happen to be known names) followed by a
    word boundary, case-sensitive, since two different family members
    could plausibly have names differing only in case. A sender
    @mentioning themselves doesn't notify them a second time on top of
    however their own message already reached them."""
    if not content or '@' not in content:
        return []
    people = [p for p in get_mentionable_users() if p['user_id'] != exclude_user_id]
    if not people:
        return []
    people.sort(key=lambda p: len(p['name']), reverse=True)
    mentioned_ids = []
    for person in people:
        # (?!\w) rather than \b — see the matching comment in
        # highlightMentions() in script.js for why: \b alone silently
        # fails to match a name that itself ends in punctuation (e.g.
        # "A.J."), since it needs a word/non-word transition that a
        # trailing non-word character followed by another non-word
        # character (a space) can never provide.
        pattern = r'@' + re.escape(person['name']) + r'(?!\w)'
        if re.search(pattern, content):
            mentioned_ids.append(person['user_id'])
    return mentioned_ids

def record_unread_mentions(channel, message_id, content, msg_type, exclude_user_id):
    """Records that specific people were @mentioned in a message, for
    the channel-list badge to count later. Deliberately separate from
    notify_message_subscribers()'s own mention detection — different
    lifetime (this persists until the channel is actually viewed;
    notifications fire once and are done) even though both start from
    the same find_mentioned_user_ids() call. calendar_event content is
    a JSON payload, not typed text, so there's nothing to scan there —
    same reasoning as the notification path."""
    if msg_type == 'calendar_event':
        return
    mentioned_ids = find_mentioned_user_ids(content, exclude_user_id=exclude_user_id)
    if not mentioned_ids:
        return
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.executemany(
        'INSERT INTO unread_mentions (user_id, channel, message_id, created_at) VALUES (?, ?, ?, ?)',
        [(uid, channel, message_id, now) for uid in mentioned_ids]
    )
    conn.commit()
    conn.close()

def get_unread_mention_counts(user_id):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT channel, COUNT(*) FROM unread_mentions WHERE user_id = ? GROUP BY channel', (user_id,))
    rows = c.fetchall()
    conn.close()
    return {channel: count for channel, count in rows}

def mark_channel_read(user_id, channel):
    """Called every time someone actually views a channel — clears
    their pending @mentions there (unread_mentions) and, separately,
    records the highest message id in the channel right now as their
    new "last read" point (channel_last_read), which is what the
    general new-message indicator is based on. One call covers both,
    since both represent the exact same real-world moment: you looked
    at this channel."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('DELETE FROM unread_mentions WHERE user_id = ? AND channel = ?', (user_id, channel))
    c.execute('SELECT MAX(id) FROM messages WHERE channel = ?', (channel,))
    max_id = (c.fetchone() or (0,))[0] or 0
    c.execute('''INSERT INTO channel_last_read (user_id, channel, last_read_message_id) VALUES (?, ?, ?)
                 ON CONFLICT(user_id, channel) DO UPDATE SET last_read_message_id = excluded.last_read_message_id
                 WHERE excluded.last_read_message_id > channel_last_read.last_read_message_id''',
              (user_id, channel, max_id))
    conn.commit()
    conn.close()

def get_unread_channels(user_id):
    """Which channels have a message newer than this person's own last
    read point, sent by someone other than them — their own messages
    don't count as "new" for themselves, the same way sending a message
    doesn't leave you with an unread badge for your own words."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''SELECT DISTINCT m.channel
                 FROM messages m
                 LEFT JOIN channel_last_read r ON r.user_id = ? AND r.channel = m.channel
                 WHERE m.id > COALESCE(r.last_read_message_id, 0)
                 AND (m.sender_id IS NULL OR m.sender_id != ?)''',
              (user_id, user_id))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

@app.route('/api/mentions/unread-counts')
def api_unread_mention_counts():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    return jsonify(get_unread_mention_counts(ha_user_id))

@app.route('/api/channels/unread-status')
def api_unread_channel_status():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    return jsonify(get_unread_channels(ha_user_id))

@app.route('/api/mentions/mark-read', methods=['POST'])
def api_mark_mentions_read():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    data = request.get_json(silent=True) or {}
    channel = (data.get('channel') or '').strip()
    if not channel:
        return jsonify({'error': 'Missing channel'}), 400
    mark_channel_read(ha_user_id, channel)
    return jsonify({'success': True})

def notify_message_subscribers(channel, sender, sender_id, content, msg_type, file_info):
    """Best-effort — a slow or failed notification should never affect
    message delivery in the chat itself, which has already happened by
    the time this is called."""
    if not SUPERVISOR_TOKEN:
        logger.info('Skipping notifications for a message in #%s — SUPERVISOR_TOKEN not set', channel)
        return

    channel_obj = next((c for c in get_channels() if c['slug'] == channel), None)
    channel_name = channel_obj['name'] if channel_obj else channel
    body = summarize_message_for_notification(content, msg_type, file_info)

    subscribers = dict(get_subscribers_for_channel(channel, exclude_user_id=sender_id))

    # Being @mentioned is a stronger, more personal signal than general
    # channel activity — it notifies you even if you never subscribed to
    # that particular channel at all, the same way it would in any other
    # chat app. Excludes only calendar_event messages, since that type's
    # content is a JSON payload, not something a person actually typed —
    # every other type (text, or a caption on an image/file/gif) is real
    # typed content worth scanning.
    mentioned_ids = find_mentioned_user_ids(content, exclude_user_id=sender_id) if msg_type != 'calendar_event' else []
    prefs_cache = {}
    for user_id in mentioned_ids:
        if user_id in subscribers:
            continue  # already getting a notification below; don't send two
        service = get_notify_service(user_id)
        if service:
            prefs_cache[user_id] = service

    if not subscribers and not prefs_cache:
        # Logged at INFO rather than staying silent — otherwise "nobody
        # is subscribed to this channel" and "this function never ran"
        # look identical in the log, which makes exactly this situation
        # (message sent, no notification, nothing to go on) impossible
        # to diagnose from the log alone.
        logger.info('No notification subscribers for #%s (message from %s)', channel, sender)
        return

    title = f'{sender} in #{channel_name}'
    for user_id, notify_service in subscribers.items():
        ok, error = send_ha_notification(notify_service, title, body)
        if ok:
            logger.info('Notified %s via %s for a message in #%s', user_id, notify_service, channel)
        else:
            logger.warning('Notification to %s via %s failed: %s', user_id, notify_service, error)

    mention_title = f'{sender} mentioned you in #{channel_name}'
    for user_id, notify_service in prefs_cache.items():
        ok, error = send_ha_notification(notify_service, mention_title, body)
        if ok:
            logger.info('Notified %s via %s for being mentioned in #%s', user_id, notify_service, channel)
        else:
            logger.warning('Mention notification to %s via %s failed: %s', user_id, notify_service, error)

@app.route('/api/notify/services')
def api_notify_services():
    """notify.* services currently registered in Home Assistant — mainly
    one per device with the HA Companion App installed (e.g.
    notify.mobile_app_johns_iphone) — so settings can offer a dropdown
    instead of making someone type a service name by hand."""
    data, error = ha_api_request('GET', '/services')
    if error:
        return jsonify({'error': error}), 503
    services = []
    for domain_entry in data or []:
        if domain_entry.get('domain') == 'notify':
            services = sorted(domain_entry.get('services', {}).keys())
            break
    return jsonify({'services': services})

@app.route('/api/notify/prefs')
def api_get_notify_prefs():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    return jsonify({
        'notify_service': get_notify_service(ha_user_id),
        'channels': get_subscribed_channels(ha_user_id),
    })

@app.route('/api/notify/prefs', methods=['POST'])
def api_set_notify_prefs():
    # Same shape as /api/my-alias: the target is always the requester's
    # own HA user ID from the ingress headers, never taken from the
    # request body, so this can only ever change your own preference.
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    data = request.get_json(silent=True) or {}
    notify_service = (data.get('notify_service') or '').strip()
    channels = data.get('channels', [])
    if not isinstance(channels, list):
        channels = []
    if channels and not notify_service:
        return jsonify({'error': 'Choose a device before subscribing to any channels.'}), 400
    # Real HA service names (what the dropdown in Settings is actually
    # populated with) only ever look like this — anything else here
    # didn't come from that dropdown.
    if notify_service and not re.fullmatch(r'(notify\.)?[a-zA-Z0-9_]+', notify_service):
        return jsonify({'error': 'That device selection is not valid.'}), 400
    set_notify_service(ha_user_id, notify_service)
    set_subscribed_channels(ha_user_id, channels)
    return jsonify({'success': True})

@app.route('/api/notify/test', methods=['POST'])
def api_notify_test():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    data = request.get_json(silent=True) or {}
    notify_service = (data.get('notify_service') or '').strip()
    if not notify_service:
        return jsonify({'error': 'Choose a device first.'}), 400
    _, sender = resolve_ha_identity()
    ok, error = send_ha_notification(
        notify_service, 'Family Chat',
        f'Test notification for {sender or "you"} — this is what new messages will look like.'
    )
    if not ok:
        return jsonify({'error': error}), 503
    return jsonify({'success': True})

# --- Calendar ---
# Creates real events on Home Assistant's own calendars via
# calendar.create_event — the same ha_api_request() plumbing already
# used for notify.* calls, just a different service. No separate
# integration or credentials of its own.

def get_calendar_entities():
    """Every calendar.* entity currently registered in Home Assistant,
    with a friendly display name. This is the *complete*, unrestricted
    list — used for the Upcoming panel (viewing every calendar's events
    is a separate concern from which ones people can add to) and as the
    source get_addable_calendar_entities() filters down from. Don't use
    this directly to validate a submitted entity_id for creating an
    event — use get_addable_calendar_entities() for that, which is the
    one that respects an admin's restriction."""
    data, error = ha_api_request('GET', '/states')
    if error:
        return None, error
    calendars = []
    for state in data or []:
        entity_id = state.get('entity_id', '')
        if entity_id.startswith('calendar.'):
            name = (state.get('attributes') or {}).get('friendly_name') or entity_id
            calendars.append({'entity_id': entity_id, 'name': name})
    calendars.sort(key=lambda c: c['name'].lower())
    return calendars, None

def get_allowed_calendar_ids():
    """None means no restriction has ever been configured — every real
    calendar is addable, which is what makes this an opt-in admin
    feature rather than something that silently breaks a fresh install
    until someone visits the admin panel. An empty list is different
    from None: that's an admin having explicitly unchecked everything,
    which is a valid (if unusual) choice to make and is honored as-is,
    not treated as "unset"."""
    raw = get_setting('allowed_calendars')
    if raw is None:
        return None
    try:
        return set(json.loads(raw))
    except (json.JSONDecodeError, TypeError):
        return None

def set_allowed_calendars(entity_ids):
    set_setting('allowed_calendars', json.dumps(sorted(set(entity_ids))))

def get_addable_calendar_entities():
    """Calendars people can actually create new events on — every real
    calendar in Home Assistant, unless an admin has restricted the list
    from the admin panel's Calendars tab, in which case only those
    remain. This is the one both the add-event dropdown and (more
    importantly) the server-side validation in
    api_create_calendar_event() should use — using the unrestricted
    get_calendar_entities() for validation would make the admin
    restriction purely cosmetic, since a crafted request could still
    name any real calendar."""
    calendars, error = get_calendar_entities()
    if error:
        return None, error
    allowed_ids = get_allowed_calendar_ids()
    if allowed_ids is None:
        return calendars, None
    return [c for c in calendars if c['entity_id'] in allowed_ids], None

@app.route('/api/calendars')
def api_calendars():
    calendars, error = get_addable_calendar_entities()
    if error:
        return jsonify({'error': error}), 503
    return jsonify({'calendars': calendars})

def get_calendar_events(entity_id, start_dt, end_dt):
    """Real events for one calendar between two datetimes, straight from
    Home Assistant's dedicated calendar REST endpoint (not the
    calendar.get_events *action* — that one's response doesn't include
    each event's uid, and the uid is exactly what makes attributing an
    event back to whoever added it through this app possible)."""
    params = urllib.parse.urlencode({
        'start': start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'end': end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
    })
    data, error = ha_api_request('GET', f'/calendars/{entity_id}?{params}')
    if error:
        return None, error
    return data or [], None

def find_event_uid(entity_id, title, all_day, start):
    """Looks a just-created event back up by querying a narrow window
    around its own start time and matching on title — the only reliable
    way to learn its uid, since calendar.create_event's own response
    doesn't include one. Best-effort: if nothing matches (a slightly
    unusual calendar integration, a timezone quirk, whatever), this
    simply returns None and the event just won't have an "added by"
    attribution later, same as any event added directly in HA."""
    try:
        if all_day:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            window_start = start_dt - timedelta(hours=12)
            window_end = start_dt + timedelta(days=2)
        else:
            start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            window_start = start_dt - timedelta(minutes=2)
            window_end = start_dt + timedelta(minutes=2)
    except ValueError:
        return None

    events, error = get_calendar_events(entity_id, window_start, window_end)
    if error or not events:
        return None
    for event in events:
        if (event.get('summary') or '').strip() == title.strip():
            return event.get('uid')
    return None

def log_calendar_event_creation(uid, entity_id, user_id, user_name):
    if not uid:
        return
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO calendar_event_log
                 (uid, entity_id, created_by_id, created_by_name, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (uid, entity_id, user_id, user_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_event_creators(uids_by_entity):
    """Bulk-fetches {(uid, entity_id): created_by_name} for a batch of
    events at once — used when building the Upcoming panel, so it's one
    query for the whole list rather than one per event."""
    if not uids_by_entity:
        return {}
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    creators = {}
    for entity_id, uids in uids_by_entity.items():
        if not uids:
            continue
        placeholders = ','.join('?' * len(uids))
        c.execute(f'SELECT uid, created_by_name FROM calendar_event_log '
                  f'WHERE entity_id = ? AND uid IN ({placeholders})',
                  [entity_id] + list(uids))
        for uid, name in c.fetchall():
            creators[(uid, entity_id)] = name
    conn.close()
    return creators

@app.route('/api/calendar/upcoming')
def api_calendar_upcoming():
    """Everything on every Home Assistant calendar over the next 60
    days, aggregated into one list and sorted by when it actually
    happens — not by when it was posted in chat, and not limited to
    events that happened to come through this app at all. That's the
    whole point of this view versus just looking at a channel: it shows
    the real calendar, exactly as Home Assistant has it."""
    calendars, error = get_calendar_entities()
    if error:
        return jsonify({'error': error}), 503

    now = datetime.now()
    window_end = now + timedelta(days=60)
    uids_by_entity = {}
    all_events = []

    for cal in calendars:
        events, cal_error = get_calendar_events(cal['entity_id'], now, window_end)
        if cal_error:
            continue  # one misbehaving calendar shouldn't blank out all the others
        for event in events:
            start = event.get('start') or {}
            end = event.get('end') or {}
            all_day = 'date' in start
            start_value = start.get('date') or start.get('dateTime') or ''
            end_value = end.get('date') or end.get('dateTime') or ''
            uid = event.get('uid')
            all_events.append({
                'uid': uid,
                'entity_id': cal['entity_id'],
                'calendar_name': cal['name'],
                'title': event.get('summary') or 'Untitled event',
                'location': event.get('location') or '',
                'all_day': all_day,
                'start': start_value,
                'end': end_value,
            })
            if uid:
                uids_by_entity.setdefault(cal['entity_id'], []).append(uid)

    creators = get_event_creators(uids_by_entity)
    for event in all_events:
        event['added_by'] = creators.get((event['uid'], event['entity_id']))
        del event['uid']  # internal only, not needed client-side

    all_events.sort(key=lambda e: e['start'])
    return jsonify({'events': all_events[:25]})

@app.route('/api/calendar/create-event', methods=['POST'])
def api_create_calendar_event():
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return jsonify({'error': 'Not accessed through Home Assistant'}), 403
    _, sender = resolve_ha_identity()

    data = request.get_json(silent=True) or {}
    entity_id = (data.get('entity_id') or '').strip()
    title = (data.get('title') or '').strip()[:200]
    all_day = bool(data.get('all_day'))
    start = (data.get('start') or '').strip()
    end = (data.get('end') or '').strip()
    location = (data.get('location') or '').strip()[:200]
    description = (data.get('description') or '').strip()[:2000]
    channel = (data.get('channel') or '').strip()

    if not title:
        return jsonify({'error': 'Give the appointment a title.'}), 400
    if not start:
        return jsonify({'error': 'Choose a start date.' if all_day else 'Choose a start date and time.'}), 400

    # entity_id and channel are both validated against the real, current
    # lists rather than trusted as-is. Using get_addable_calendar_entities()
    # here specifically — not the unrestricted get_calendar_entities() —
    # is what actually enforces an admin's calendar restriction; using
    # the unrestricted list would make that restriction purely cosmetic,
    # since a crafted request could still name any real calendar.
    calendars, cal_error = get_addable_calendar_entities()
    if cal_error:
        return jsonify({'error': cal_error}), 503
    if entity_id not in {c['entity_id'] for c in calendars}:
        return jsonify({'error': 'Choose a valid calendar.'}), 400

    valid_channels = {c['slug'] for c in get_channels()}
    if channel not in valid_channels:
        channel = 'general'

    event_body = {'entity_id': entity_id, 'summary': title}
    if location:
        event_body['location'] = location
    if description:
        event_body['description'] = description

    if all_day:
        # HA's end date is exclusive (a single-day all-day event on
        # 2024-03-10 needs an end date of 2024-03-11) — if the form only
        # collected a start date (the common case: a one-day event), the
        # end is computed here rather than requiring the person to
        # understand and manually enter "the day after."
        if not end:
            try:
                start_date = datetime.strptime(start, '%Y-%m-%d')
                end = (start_date + timedelta(days=1)).strftime('%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid start date.'}), 400
        event_body['start_date'] = start
        event_body['end_date'] = end
    else:
        if not end:
            return jsonify({'error': 'Choose an end time.'}), 400
        event_body['start_date_time'] = start
        event_body['end_date_time'] = end

    _, error = ha_api_request('POST', '/services/calendar/create_event', event_body)
    if error:
        return jsonify({'error': error}), 503

    # Best-effort attribution — the event is already successfully
    # created in Home Assistant regardless of whether this lookup
    # succeeds, so nothing here should ever fail the request itself.
    uid = find_event_uid(entity_id, title, all_day, start)
    log_calendar_event_creation(uid, entity_id, ha_user_id, sender)

    # Posts the same way any other message does — saved, then broadcast
    # to whichever channel's room it belongs to — except this request
    # came in over plain HTTP, not an active socket connection, so it
    # uses socketio.emit() (the SocketIO instance's own method) rather
    # than the bare emit() imported from flask_socketio, which only
    # works from inside an actual @socketio.on(...) handler's request
    # context. content is a small JSON payload, not display text — the
    # client renders it as a card; see buildCalendarEventHtml() in
    # script.js. summarize_message_for_notification() and the search
    # endpoint both know how to turn this same payload into a plain-text
    # summary for contexts that can't render the card.
    event_payload = {
        'title': title, 'all_day': all_day, 'start': start, 'end': end, 'location': location,
    }
    msg_id = save_message(sender, json.dumps(event_payload), channel, 'calendar_event', sender_id=ha_user_id)
    socketio.emit('new_message', {
        'id': msg_id,
        'sender': sender,
        'sender_id': ha_user_id,
        'avatar_url': get_avatar(ha_user_id) if ha_user_id else None,
        'content': json.dumps(event_payload),
        'timestamp': datetime.now().isoformat(),
        'channel': channel,
        'type': 'calendar_event',
        'file': None,
        'reactions': {}
    }, room=channel)
    notify_message_subscribers(channel, sender, ha_user_id, json.dumps(event_payload), 'calendar_event', None)

    return jsonify({'success': True, 'channel': channel})

def log_socket_errors(handler):
    """Socket.IO event handlers don't go through Flask's normal error
    handling — an unhandled exception in one can otherwise just vanish
    with the client never knowing anything happened. This logs the full
    traceback and tells the client something went wrong, instead of a
    message silently failing to send."""
    @functools.wraps(handler)
    def wrapped(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except Exception:
            logger.exception('Unhandled error in socket handler %s', handler.__name__)
            try:
                emit('server_error', {
                    'message': "That didn't go through — check the add-on log for details."
                })
            except Exception:
                pass
    return wrapped

@socketio.on('connect')
@log_socket_errors
def handle_connect(auth=None):
    logger.info('Client connected')

@socketio.on('join')
@log_socket_errors
def on_join(data):
    room = data.get('room', 'general')
    # Switching channels previously only ever *joined* the new room and
    # never left the old one — a session that visited every channel over
    # time would end up subscribed to all of them simultaneously, so
    # messages posted anywhere would land in whichever channel you
    # happened to be looking at. Every socket's own default room is its
    # sid, which must stay untouched; leave everything else before
    # joining the requested channel so a connection is only ever in the
    # one channel room it's actually viewing.
    for r in list(rooms()):
        if r != request.sid:
            leave_room(r)
    join_room(room)
    emit('joined', {'room': room})

@socketio.on('send_message')
@log_socket_errors
def handle_message(data):
    # Identity is resolved server-side from the Home Assistant ingress
    # headers, not taken from the client payload — otherwise anyone could
    # still claim to be a different family member by editing the socket
    # message, defeating the point of removing the manual picker.
    sender_id, sender = resolve_ha_identity()
    content = (data.get('content') or '').strip()
    channel = data.get('channel', 'general')
    msg_type = data.get('type', 'text')
    file_info = data.get('file', None)
    
    if not sender:
        logger.warning('send_message from a request with no resolvable HA identity (sender_id=%s)', sender_id)
        emit('server_error', {'message': "Couldn't identify you as a Home Assistant user — try reloading the page."})
        return

    # Nothing previously capped message length — an unbounded socket
    # payload gets stored as-is and broadcast to everyone in the
    # channel, then re-fetched on every future page load by every
    # member, so this is both a storage-bloat and bandwidth concern, not
    # just a display one. 4000 characters is generous for a chat message
    # while still being a hard ceiling.
    if len(content) > 4000:
        emit('server_error', {'message': 'That message is too long (4000 characters max).'})
        return
    if not content and not file_info:
        return

    file_url = file_info.get('url') if file_info else None
    file_name = file_info.get('filename') if file_info else None
    file_size = file_info.get('size') if file_info else None
    mime_type = file_info.get('mime_type') if file_info else None
    
    msg_id = save_message(sender, content, channel, msg_type,
                         file_url, file_name, file_size, mime_type,
                         sender_id=sender_id)
    record_unread_mentions(channel, msg_id, content, msg_type, sender_id)
    
    emit('new_message', {
        'id': msg_id,
        'sender': sender,
        'sender_id': sender_id,
        'avatar_url': get_avatar(sender_id) if sender_id else None,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'channel': channel,
        'type': msg_type,
        'file': file_info,
        'reactions': {}
    }, room=channel)

    # In-app delivery above has already happened — this reaches people
    # who subscribed to push notifications, whether or not the chat is
    # even open on their phone right now. Deliberately last: never let a
    # slow/failed notification delay the message actually showing up.
    notify_message_subscribers(channel, sender, sender_id, content, msg_type, file_info)

@socketio.on('add_reaction')
@log_socket_errors
def handle_reaction(data):
    message_id = data.get('message_id')
    emoji = data.get('emoji')
    _, user = resolve_ha_identity()

    if not (message_id and emoji and user):
        return

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()

    c.execute('SELECT channel FROM messages WHERE id = ?', (message_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    channel = row[0]

    # A reaction click is a toggle: clicking the same emoji you've
    # already placed on this message removes it again — this is what the
    # "active"/highlighted pill styling in the UI has always implied, but
    # the server previously just inserted a new row every time, so a
    # second click silently added a duplicate instead of un-reacting.
    c.execute('SELECT id FROM reactions WHERE message_id = ? AND emoji = ? AND user = ?',
              (message_id, emoji, user))
    existing = c.fetchone()
    if existing:
        c.execute('DELETE FROM reactions WHERE id = ?', (existing[0],))
        added = False
    else:
        c.execute('INSERT INTO reactions (message_id, emoji, user) VALUES (?, ?, ?)',
                  (message_id, emoji, user))
        added = True
    conn.commit()
    conn.close()

    emit('reaction_updated', {
        'message_id': message_id,
        'emoji': emoji,
        'user': user,
        'added': added
    }, room=channel)

@socketio.on('delete_message')
@log_socket_errors
def handle_delete_message(data):
    message_id = data.get('message_id')
    requester_id, requester_name = resolve_ha_identity()
    can_manage = bool(session.get('is_admin')) or is_owner(requester_id)

    if not message_id:
        return
    if not requester_id and not can_manage:
        emit('server_error', {'message': "Couldn't identify you as a Home Assistant user — try reloading the page."})
        return

    channel, error = delete_message(message_id, requester_id, can_manage)
    if error:
        emit('server_error', {'message': error})
        return

    emit('message_deleted', {'message_id': message_id}, room=channel)

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=8099, debug=False)
