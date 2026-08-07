#!/usr/bin/env python3
import asyncio
import json
import os
import sqlite3
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
import eventlet

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configuration
USERNAME1 = os.environ.get('USERNAME1', 'Family Member 1')
USERNAME2 = os.environ.get('USERNAME2', 'Family Member 2')
THEME = os.environ.get('THEME', 'dark')
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '25')) * 1024 * 1024

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
    
    conn.commit()
    conn.close()

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

@app.route('/')
def index():
    return render_template('index.html', 
                          username1=USERNAME1, 
                          username2=USERNAME2,
                          theme=THEME)

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
    created_by = request.form.get('created_by', 'unknown')
    
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
        return jsonify({'success': True, 'name': f':{name}:'})
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
    sender = data.get('sender')
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
    user = data.get('user')
    
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
