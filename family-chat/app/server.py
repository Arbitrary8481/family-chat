#!/usr/bin/env python3
import asyncio
import functools
import hmac
import json
import os
import re
import secrets
import sqlite3
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import eventlet

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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

# Configuration
THEME = get_option('theme', 'THEME', 'dark')
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '25')) * 1024 * 1024

ADMIN_PASSWORD = get_option('admin_password', 'ADMIN_PASSWORD', 'changeme')
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)
if ADMIN_PASSWORD == 'changeme':
    print('WARNING: admin_password is still set to the default "changeme". '
          'Set it in the add-on configuration.')

# Cache-busting token for static assets (CSS/JS). Home Assistant's ingress
# "soft" panel navigation (clicking the sidebar entry again) can reuse a
# browser-cached copy of style.css instead of always fetching fresh, which
# shows up as "styling doesn't apply until I hit refresh". Appending this
# to asset URLs (?v=...) and disabling caching on the static route below
# means every container start serves guaranteed-fresh assets.
ASSET_VERSION = str(int(datetime.now().timestamp()))

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
                  mime_type TEXT)''')
    
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
    each person's own HA display name (or username as a fallback)."""
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT display_name, username FROM ha_users ORDER BY last_seen DESC')
    rows = c.fetchall()
    conn.close()
    seen = set()
    people = []
    for display_name, username in rows:
        name = (display_name or '').strip() or (username or '').strip()
        if name and name not in seen:
            seen.add(name)
            people.append(name)
    return people

def slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '-', text.strip().lower()).strip('-')
    return slug[:30]

def get_channels():
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT slug, name, icon FROM channels ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return [{'slug': r[0], 'name': r[1], 'icon': r[2]} for r in rows]

def add_channel(name, icon):
    name = name.strip()[:30]
    icon = (icon.strip() or '#')[:8]
    slug = slugify(name)
    if not name or not slug:
        return None, 'Channel name is required.'

    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM channels WHERE slug = ?', (slug,))
    if c.fetchone():
        conn.close()
        return None, 'A channel with that name already exists.'
    c.execute('INSERT INTO channels (slug, name, icon) VALUES (?, ?, ?)', (slug, name, icon))
    conn.commit()
    conn.close()
    return slug, None

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
    c.execute('''SELECT m.*, GROUP_CONCAT(r.emoji || ':' || r.user) as reactions
                 FROM messages m
                 LEFT JOIN reactions r ON m.id = r.message_id
                 WHERE m.channel = ?
                 GROUP BY m.id
                 ORDER BY m.timestamp DESC LIMIT ?''', (channel, limit))
    messages = c.fetchall()
    
    # Get columns
    columns = [description[0] for description in c.description]
    result = []
    for row in messages:
        msg = dict(zip(columns, row))
        # Parse reactions
        if msg['reactions']:
            reactions = {}
            for r in msg['reactions'].split(','):
                if ':' in r:
                    emoji, user = r.split(':', 1)
                    if emoji not in reactions:
                        reactions[emoji] = []
                    reactions[emoji].append(user)
            msg['reactions'] = reactions
        else:
            msg['reactions'] = {}
        result.append(msg)
    
    conn.close()
    return list(reversed(result))

def save_message(sender, content, channel='general', msg_type='text', 
                 file_url=None, file_name=None, file_size=None, mime_type=None):
    conn = sqlite3.connect('/data/chat.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('''INSERT INTO messages 
                 (sender, content, timestamp, channel, message_type, 
                  file_url, file_name, file_size, mime_type) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (sender, content, timestamp, channel, msg_type,
               file_url, file_name, file_size, mime_type))
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id

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
    """
    prefix = request.headers.get('X-Ingress-Path', '')
    if not prefix.startswith('/') or ':' in prefix:
        prefix = ''
    return redirect(prefix + path)

@app.after_request
def set_static_cache_headers(response):
    if request.path.startswith('/static/'):
        # "no-cache" still lets the browser cache the file, but forces it
        # to revalidate with the server (a cheap conditional GET) instead
        # of silently reusing a stale copy — which is what was causing
        # stale CSS to stick around across Home Assistant's ingress "soft"
        # panel reloads until a manual refresh.
        response.headers['Cache-Control'] = 'no-cache'
    return response

def resolve_ha_identity():
    """The chat name is always the logged-in Home Assistant user's own
    name — there's no admin mapping step. Prefers the display name set on
    their HA profile (what HA itself shows for them); falls back to their
    login username if that's blank. Returns (ha_user_id, chat_name);
    chat_name is None only if there's no HA identity at all (e.g. accessed
    outside ingress)."""
    ha_user_id = request.headers.get('X-Remote-User-Id')
    if not ha_user_id:
        return None, None
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
    _, auto_user = resolve_ha_identity()

    return render_template('index.html',
                          members=[{'name': n} for n in get_known_people()],
                          theme=THEME,
                          asset_version=ASSET_VERSION,
                          inline_css=INLINE_CSS,
                          channels=get_channels(),
                          auto_user=auto_user)

@app.route('/api/channels')
def api_channels():
    return jsonify(get_channels())

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return render_template('admin.html', logged_in=False, error=request.args.get('error'))
    return render_template('admin.html', logged_in=True,
                          saved=request.args.get('saved'),
                          channels=get_channels(),
                          channel_error=request.args.get('channel_error'))

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.form.get('password', '')
    # Constant-time-safe comparison via check_password_hash (hmac.compare_digest internally)
    if check_password_hash(ADMIN_PASSWORD_HASH, password):
        session['is_admin'] = True
        return ingress_redirect(url_for('admin_panel'))
    return ingress_redirect(url_for('admin_panel', error='Incorrect password'))

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return ingress_redirect(url_for('admin_panel'))

@app.route('/admin/channels/add', methods=['POST'])
@require_admin
def admin_add_channel():
    name = request.form.get('name', '')
    icon = request.form.get('icon', '#')
    slug, error = add_channel(name, icon)
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error))
    return ingress_redirect(url_for('admin_panel', saved='1'))

@app.route('/admin/channels/delete', methods=['POST'])
@require_admin
def admin_delete_channel():
    slug = request.form.get('slug', '')
    ok, error = delete_channel(slug)
    if error:
        return ingress_redirect(url_for('admin_panel', channel_error=error))
    return ingress_redirect(url_for('admin_panel', saved='1'))

@app.route('/api/messages')
def get_messages_api():
    channel = request.args.get('channel', 'general')
    return jsonify(get_messages(channel=channel))

@app.route('/api/emojis')
def get_emojis():
    return jsonify(get_custom_emojis())

@app.route('/api/upload', methods=['POST'])
def upload_file():
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
    
    filename = f"emoji_{name}_{int(datetime.now().timestamp())}.{ext}"
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

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('join')
def on_join(data):
    room = data.get('room', 'general')
    join_room(room)
    emit('joined', {'room': room})

@socketio.on('send_message')
def handle_message(data):
    # Identity is resolved server-side from the Home Assistant ingress
    # headers, not taken from the client payload — otherwise anyone could
    # still claim to be a different family member by editing the socket
    # message, defeating the point of removing the manual picker.
    _, sender = resolve_ha_identity()
    content = data.get('content')
    channel = data.get('channel', 'general')
    msg_type = data.get('type', 'text')
    file_info = data.get('file', None)
    
    if sender:
        file_url = file_info.get('url') if file_info else None
        file_name = file_info.get('filename') if file_info else None
        file_size = file_info.get('size') if file_info else None
        mime_type = file_info.get('mime_type') if file_info else None
        
        msg_id = save_message(sender, content, channel, msg_type,
                             file_url, file_name, file_size, mime_type)
        
        emit('new_message', {
            'id': msg_id,
            'sender': sender,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'channel': channel,
            'type': msg_type,
            'file': file_info,
            'reactions': {}
        }, broadcast=True)

@socketio.on('add_reaction')
def handle_reaction(data):
    message_id = data.get('message_id')
    emoji = data.get('emoji')
    _, user = resolve_ha_identity()
    
    if message_id and emoji and user:
        conn = sqlite3.connect('/data/chat.db')
        c = conn.cursor()
        c.execute('INSERT INTO reactions (message_id, emoji, user) VALUES (?, ?, ?)',
                  (message_id, emoji, user))
        conn.commit()
        conn.close()
        
        emit('reaction_added', {
            'message_id': message_id,
            'emoji': emoji,
            'user': user
        }, broadcast=True)

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=8099, debug=False)
