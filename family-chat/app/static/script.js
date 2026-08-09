// Global state
let socket;
let currentUser = null;

function getStoredChannel() {
    // Only trust a stored channel if it still actually exists — an admin
    // may have deleted it since it was last saved.
    try {
        const stored = localStorage.getItem('lastChannel');
        if (stored && document.querySelector(`.channel[data-channel="${CSS.escape(stored)}"]`)) {
            return stored;
        }
    } catch (e) {}
    return null;
}

let currentChannel = getStoredChannel() || window.DEFAULT_CHANNEL || 'general';
let selectedFile = null;
let customEmojis = {};
let recentEmojis = JSON.parse(localStorage.getItem('recentEmojis') || '[]');

// Standard emoji categories
const emojiCategories = {
    people: ['😀','😃','😄','😁','😅','😂','🤣','😊','😇','🙂','🙃','😉','😌','😍','🥰','😘','😗','😙','😚','😋','😛','😝','😜','🤪','🤨','🧐','🤓','😎','🥸','🤩','🥳','😏','😒','😞','😔','😟','😕','🙁','☹️','😣','😖','😫','😩','🥺','😢','😭','😤','😠','😡','🤬','🤯','😳','🥵','🥶','😱','😨','😰','😥','😓','🤗','🤔','🤭','🤫','🤥','😶','😐','😑','😬','🙄','😯','😦','😧','😮','😲','🥱','😴','🤤','😪','😵','🤐','🥴','🤢','🤮','🤧','😷','🤒','🤕','🤑','🤠','😈','👿','👹','👺','🤡','💩','👻','💀','☠️','👽','👾','🤖','🎃','😺','😸','😹','😻','😼','😽','🙀','😿','😾','🤲','👐','🙌','👏','🤝','👍','👎','👊','✊','🤛','🤜','🤞','✌️','🤟','🤘','👌','🤏','👈','👉','👆','👇','☝️','✋','🤚','🖐️','🖖','👋','🤙','💪','🦾','🖕','✍️','🙏','🦶','🦵','🦿','💄','💋','👄','🦷','👅','👂','🦻','👃','👣','👁️','👀','🧠','🫀','🫁','🦴','🦷','👀'],
    nature: ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐽','🐸','🐵','🙈','🙉','🙊','🐒','🐔','🐧','🐦','🐤','🐣','🐥','🦆','🦅','🦉','🦇','🐺','🐗','🐴','🦄','🐝','🐛','🦋','🐌','🐞','🐜','🦟','🦗','🕷️','🕸️','🦂','🐢','🐍','🦎','🦖','🦕','🐙','🦑','🦐','🦞','🦀','🐡','🐠','🐟','🐬','🐳','🐋','🦈','🐊','🐅','🐆','🦓','🦍','🦧','🐘','🦛','🦏','🐪','🐫','🦒','🦘','🐃','🐂','🐄','🐎','🐖','🐏','🐑','🦙','🐐','🦌','🐕','🐩','🦮','🐕‍🦺','🐈','🐈‍⬛','🐓','🦃','🦚','🦜','🦢','🦩','🕊️','🐇','🦝','🦨','🦡','🦦','🦥','🐁','🐀','🐿️','🦔','🐾','🐉','🐲','🌵','🎄','🌲','🌳','🌴','🌱','🌿','☘️','🍀','🎍','🎋','🍃','🍂','🍁','🍄','🐚','🌾','💐','🌷','🌹','🥀','🌺','🌸','🌼','🌻','🌞','🌝','🌛','🌜','🌚','🌕','🌖','🌗','🌘','🌑','🌒','🌓','🌔','🌙','🌎','🌍','🌏','🪐','💫','⭐','🌟','✨','⚡','🔥','💥','☄️','☀️','🌤️','⛅','🌥️','🌦️','🌈','☁️','🌧️','⛈️','🌩️','🌨️','❄️','☃️','⛄','🌬️','💨','💧','💦','☔','☂️','🌊','🌫️'],
    food: ['🍏','🍎','🍐','🍊','🍋','🍌','🍉','🍇','🍓','🍈','🍒','🍑','🍍','🥝','🥥','🥑','🍆','🍅','🌶️','🥒','🥬','🥦','🧄','🧅','🍄','🥜','🌰','🍞','🥐','🥖','🥨','🥯','🥞','🧇','🧀','🍖','🍗','🥩','🥓','🍔','🍟','🍕','🌭','🥪','🌮','🌯','🥙','🧆','🥚','🍳','🥘','🍲','🥣','🥗','🍿','🧈','🧂','🥫','🍱','🍘','🍙','🍚','🍛','🍜','🍝','🍠','🍢','🍣','🍤','🍥','🍡','🍦','🍧','🍨','🍩','🍪','🎂','🍰','🧁','🥧','🍫','🍬','🍭','🍮','🍯','🍼','🥛','☕','🍵','🧃','🥤','🍶','🍺','🍻','🥂','🍷','🥃','🍸','🍹','🧉','🍾','🧊','🥄','🍴','🍽️','🥣','🥡','🥢','🧂'],
    activities: ['⚽','🏀','🏈','⚾','🥎','🎾','🏐','🏉','🥏','🎱','🪀','🏓','🏸','🏒','🏑','🥍','🏏','🥅','⛳','🪁','🏹','🎣','🤿','🥊','🥋','🎽','🛹','🛷','⛸️','🥌','🎿','⛷️','🏂','🏋️','🤼','🤽','🤾','🤺','🏇','⛷️','🏂','🏌️','🏄','🚣','🏊','⛹️','🏋️','🚴','🚵','🎽','🎿','🛷','🥅','⛳','🎣','🎽','🎿','🎯','🎱','🔮','🧿','🎮','🕹️','🎰','🎲','🧩','🧸','🪅','🪆','♠️','♥️','♦️','♣️','♟️','🃏','🀄','🎴','🎭','🖼️','🎨','🧵','🧶','🥼','🥽','🥾','🥿','👟','👞','🥾','🥿','👠','👡','👢','👑','👒','🎩','🎓','🧢','⛑️','📿','💄','💍','💎','🔇','🔈','🔉','🔊','📢','📣','📯','🔔','🔕','🎼','🎵','🎶','🎙️','🎚️','🎛️','🎤','🎧','📻','🎷','🎸','🎹','🎺','🎻','🪕','🥁','📱','📲','☎️','📞','📟','📠','🔋','🔌','💻','🖥️','🖨️','⌨️','🖱️','🖲️','💽','💾','💿','📀','🧮','🎥','🎞️','📽️','🎬','📺','📷','📸','📹','📼','🔍','🔎','🕯️','💡','🔦','🏮','🪔','📔','📕','📖','📗','📘','📙','📚','📓','📒','📃','📜','📄','📰','🗞️','📑','🔖','🏷️','💰','🪙','💴','💵','💶','💷','💸','💳','🧾','💹','✉️','📧','📨','📩','📤','📥','📦','📫','📪','📬','📭','📮','🗳️','✏️','✒️','🖋️','🖊️','🖌️','🖍️','📝','💼','📁','📂','🗂️','📅','📆','🗒️','🗓️','📇','📈','📉','📊','📋','📌','📍','📎','🖇️','📏','📐','✂️','🗃️','🗄️','🗑️','🔒','🔓','🔏','🔐','🔑','🗝️','🔨','🪓','⛏️','⚒️','🛠️','🗡️','⚔️','🔫','🏹','🛡️','🔧','🔩','⚙️','🗜️','⚖️','🦯','🔗','⛓️','🧰','🧲','🧪','🧫','🧬','🔬','🔭','📡','💉','🩸','💊','🩹','🩺','🌡️','🚽','🚰','🚿','🛁','🛀','🧴','🧷','🧹','🧺','🧻','🧼','🧽','🧯','🛒','🚬','⚰️','⚱️','🗿','🚂','🚃','🚄','🚅','🚆','🚇','🚈','🚉','🚊','🚝','🚞','🚋','🚌','🚍','🚎','🚐','🚑','🚒','🚓','🚔','🚕','🚖','🚗','🚘','🚙','🚚','🚛','🚜','🏎️','🏍️','🛵','🦽','🦼','🛺','🚲','🛴','🛹','🛼','🚏','🛣️','🛤️','🛢️','⛽','🚨','🚥','🚦','🛑','🚧','⚓','⛵','🛶','🚤','🛳️','⛴️','🚢','✈️','🛩️','🛫','🛬','🪂','💺','🚁','🚟','🚠','🚡','🛰️','🚀','🛸','🛎️','🧳','⌛','⏳','⌚','⏰','⏱️','⏲️','🕰️','🕛','🕧','🕐','🕜','🕑','🕝','🕒','🕞','🕓','🕟','🕔','🕠','🕕','🕡','🕖','🕢','🕗','🕣','🕘','🕤','🕙','🕥','🕚','🕦','🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘','🌙','🌚','🌛','🌜','🌡️','☀️','🌝','🌞','🪐','⭐','🌟','🌠','🌌','☁️','⛅','⛈️','🌤️','🌥️','🌦️','🌧️','🌨️','🌩️','🌪️','🌫️','🌬️','🌀','🌈','🌂','☂️','☔','⛱️','⚡','❄️','☃️','⛄','☄️','🔥','💧','🌊']
};

// Initialize everything after DOM is ready.
// Identity is resolved entirely by the server from the Home Assistant
// ingress login (see the /admin HA-mapping section) — there's no manual
// picker anymore. If Home Assistant couldn't resolve a name, the
// identityGate stays visible with instructions instead of the chat.
document.addEventListener('DOMContentLoaded', function() {
    if (window.AUTO_CHAT_USER) {
        currentUser = window.AUTO_CHAT_USER;
        const gate = document.getElementById('identityGate');
        if (gate) gate.classList.add('hidden');

        const usernameEl = document.getElementById('currentUsername');
        const avatarEl = document.getElementById('currentAvatar');
        if (usernameEl) usernameEl.textContent = currentUser;
        if (avatarEl) avatarEl.textContent = currentUser[0];

        initializeChat();
    }
    // else: leave identityGate visible (server already rendered the right
    // message — "ask an admin" vs "open via Home Assistant").
});

// All other functions below...

// Home Assistant ingress serves this app under a dynamic prefix like
// /api/hassio_ingress/<token>/ instead of the domain root. socket.io's
// default path option ("/socket.io/") ignores that prefix, so the
// WebSocket handshake gets routed wrong and never reaches the server.
// Deriving the path from the current URL fixes it for both ingress and
// plain (non-ingress) access.
function getIngressBasePath() {
    const path = window.location.pathname;
    return path.endsWith('/') ? path : path.substring(0, path.lastIndexOf('/') + 1);
}

// The server returns root-relative API paths ("/api/messages") and file
// URLs ("/uploads/x.png"). A root-relative path resolves from the domain
// root in the browser, not from the current ingress-prefixed page, so
// under Home Assistant ingress every fetch() and every <img>/<video>/<a>
// pointed at one of these would silently 404. These two helpers rewrite
// them to be relative to the current (possibly ingress-prefixed) page.
function apiUrl(path) {
    return getIngressBasePath() + path.replace(/^\//, '');
}

function resolveUrl(url) {
    if (!url || !url.startsWith('/')) return url;
    return getIngressBasePath() + url.slice(1);
}

function initializeChat() {
    const basePath = getIngressBasePath();
    socket = io(window.location.origin, {
        path: basePath + 'socket.io/'
    });

    // The server always renders the first channel as "active" in the
    // initial HTML. If a different channel was restored from storage,
    // fix the sidebar/header to match it before anything loads — 
    // otherwise the highlighted channel and the messages shown for it
    // disagree with each other.
    document.querySelectorAll('.channel').forEach(ch => {
        ch.classList.toggle('active', ch.dataset.channel === currentChannel);
    });
    const initialChannelEl = document.getElementById('currentChannel');
    const initialWelcomeEl = document.getElementById('welcomeChannel');
    const initialInputEl = document.getElementById('messageInput');
    if (initialChannelEl) initialChannelEl.textContent = currentChannel;
    if (initialWelcomeEl) initialWelcomeEl.textContent = currentChannel;
    if (initialInputEl) initialInputEl.placeholder = `Message #${currentChannel}`;
    
    socket.on('connect', function() {
        console.log('Connected to server');
        socket.emit('join', {room: currentChannel});
    });
    
    socket.on('new_message', function(data) {
        addMessage(data);
        scrollToBottom();
        
        if (data.type === 'image' || data.type === 'gif' || (data.file && data.file.mime_type && data.file.mime_type.startsWith('image/'))) {
            addToSharedMedia(resolveUrl(data.file.url));
        }
    });
    
    socket.on('reaction_added', function(data) {
        updateReaction(data.message_id, data.emoji, data.user);
    });

    // If something goes wrong server-side while handling an event (a
    // failed send, a bad reaction, etc.), this is what used to fail
    // completely silently — now at least tell the person something broke.
    socket.on('server_error', function(data) {
        alert(data.message || 'Something went wrong. Check the add-on log for details.');
    });
    
    fetch(apiUrl(`/api/messages?channel=${currentChannel}`))
        .then(r => r.json())
        .then(messages => {
            messages.forEach(msg => addMessage(msg));
            scrollToBottomRobust();
        });
    
    fetch(apiUrl('/api/emojis'))
        .then(r => r.json())
        .then(emojis => {
            customEmojis = emojis;
        });
    
    const input = document.getElementById('messageInput');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessageClick();
            }
        });
    }
    
    document.querySelectorAll('.channel').forEach(ch => {
        ch.addEventListener('click', function() {
            switchChannel(this.dataset.channel);
        });
    });
    
    loadEmojiCategory('people');
}

function sendMessageClick() {
    const input = document.getElementById('messageInput');
    if (!input) return;
    
    const content = input.value.trim();
    
    if (content || selectedFile) {
        sendMessage(content);
        input.value = '';
    }
}

function sendMessage(content) {
    const msgData = {
        sender: currentUser,
        content: content,
        channel: currentChannel,
        type: 'text'
    };
    
    if (selectedFile) {
        msgData.file = selectedFile;
        msgData.type = selectedFile.mime_type.startsWith('image/') ? 'image' : 
                       selectedFile.mime_type.startsWith('video/') ? 'video' : 'file';
        selectedFile = null;
        closeFileModal();
    }
    
    socket.emit('send_message', msgData);
}

function addMessage(data) {
    const container = document.getElementById('messagesContainer');
    if (!container) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.dataset.id = data.id;
    
    const time = new Date(data.timestamp).toLocaleTimeString([], {
        hour: '2-digit', 
        minute: '2-digit'
    });
    
    let contentHtml = `<div class="message-text">${escapeHtml(data.content || '')}</div>`;
    
    if (data.file || data.file_url) {
        const fileUrl = safeUrl(resolveUrl(data.file?.url || data.file_url));
        const fileName = escapeHtml(data.file?.filename || data.file_name);
        const mimeType = escapeHtml(data.file?.mime_type || data.mime_type);
        
        if (mimeType && mimeType.startsWith('image/')) {
            contentHtml += `
                <div class="message-image" onclick="openImageViewer('${fileUrl}')">
                    <img src="${fileUrl}" alt="${fileName}" loading="lazy">
                </div>
            `;
        } else if (mimeType && mimeType.startsWith('video/')) {
            contentHtml += `
                <div class="message-video">
                    <video controls preload="metadata">
                        <source src="${fileUrl}" type="${mimeType}">
                    </video>
                </div>
            `;
        } else {
            const fileSize = formatFileSize(data.file?.size || data.file_size || 0);
            const fileIcon = getFileIcon(mimeType);
            contentHtml += `
                <div class="message-file">
                    <a href="${fileUrl}" target="_blank" class="file-attachment">
                        <div class="file-icon">${fileIcon}</div>
                        <div class="file-info">
                            <div class="file-name">${fileName}</div>
                            <div class="file-size">${fileSize}</div>
                        </div>
                    </a>
                </div>
            `;
        }
    }
    
    let reactionsHtml = '';
    if (data.reactions && Object.keys(data.reactions).length > 0) {
        reactionsHtml = '<div class="message-reactions">';
        for (const [emoji, users] of Object.entries(data.reactions)) {
            const isActive = users.includes(currentUser);
            const safeEmoji = escapeHtml(emoji);
            reactionsHtml += `
                <div class="reaction ${isActive ? 'active' : ''}" onclick="toggleReaction(${data.id}, '${safeEmoji}')">
                    ${safeEmoji} <span class="reaction-count">${users.length}</span>
                </div>
            `;
        }
        reactionsHtml += '</div>';
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${data.sender[0]}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${escapeHtml(data.sender)}</span>
                <span class="message-timestamp">${time}</span>
            </div>
            ${contentHtml}
            ${reactionsHtml}
        </div>
        <div class="message-actions">
            <button class="action-btn" onclick="addReaction(${data.id})" title="Add reaction">😊</button>
        </div>
    `;
    
    container.appendChild(messageDiv);
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) container.scrollTop = container.scrollHeight;
}

// Images finish loading asynchronously, after they've already been
// inserted into the DOM — each one that loads grows the page a bit more.
// A single scrollToBottom() called right after rendering measures the
// page before that growth happens, so on a channel with attachments you
// can land noticeably above the actual most recent message. This re-runs
// the scroll whenever a newly-added image finishes loading (or fails to).
function scrollToBottomRobust() {
    scrollToBottom();
    const container = document.getElementById('messagesContainer');
    if (!container) return;
    container.querySelectorAll('img').forEach(img => {
        if (!img.complete) {
            img.addEventListener('load', scrollToBottom, { once: true });
            img.addEventListener('error', scrollToBottom, { once: true });
        }
    });
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    // Escaping quotes too (not just <, >, &) matters because this value
    // often gets dropped into an HTML *attribute* (onclick="...", alt="..."),
    // not just text content — a bare quote character there breaks out of
    // the attribute and enables injecting arbitrary attributes/handlers.
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function safeUrl(url) {
    // Only allow relative paths or http(s) URLs into src/href attributes.
    // Without this, a spoofed file/emoji URL (these can still be
    // client-supplied in the socket payload) could use a "javascript:" or
    // "data:" scheme to run script when clicked/rendered.
    if (!url) return '#';
    const s = String(url);
    if (s.startsWith('/') || s.startsWith('./') || s.startsWith('http://') || s.startsWith('https://')) {
        return escapeHtml(s);
    }
    return '#';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(mimeType) {
    if (mimeType?.startsWith('image/')) return '🖼️';
    if (mimeType?.startsWith('video/')) return '🎬';
    if (mimeType?.startsWith('audio/')) return '🎵';
    if (mimeType?.includes('pdf')) return '📄';
    return '📎';
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    fetch(apiUrl('/api/upload'), {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            selectedFile = data;
            showFilePreview(data, file);
        } else {
            alert('Upload failed: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Upload error:', err);
        alert('Upload failed');
    });
    
    event.target.value = '';
}

function showFilePreview(data, file) {
    const modal = document.getElementById('fileModal');
    const content = document.getElementById('filePreviewContent');
    if (!modal || !content) return;
    
    if (data.mime_type.startsWith('image/')) {
        content.innerHTML = `<img src="${safeUrl(resolveUrl(data.url))}" alt="${escapeHtml(data.filename)}">`;
    } else if (data.mime_type.startsWith('video/')) {
        content.innerHTML = `<video controls><source src="${safeUrl(resolveUrl(data.url))}" type="${escapeHtml(data.mime_type)}"></video>`;
    } else {
        content.innerHTML = `
            <div class="file-attachment" style="padding: 32px;">
                <div class="file-icon" style="width: 64px; height: 64px; font-size: 32px;">${getFileIcon(data.mime_type)}</div>
                <div class="file-info">
                    <div class="file-name">${escapeHtml(data.filename)}</div>
                    <div class="file-size">${formatFileSize(data.size)}</div>
                </div>
            </div>
        `;
    }
    
    modal.classList.remove('hidden');
}

function closeFileModal() {
    const modal = document.getElementById('fileModal');
    if (modal) modal.classList.add('hidden');
    selectedFile = null;
}

function sendFile() {
    const captionInput = document.getElementById('fileCaption');
    const caption = captionInput ? captionInput.value : '';
    sendMessage(caption);
}

function toggleEmojiPicker() {
    const picker = document.getElementById('emojiPicker');
    if (!picker) return;
    const gifPicker = document.getElementById('gifPicker');
    if (gifPicker) gifPicker.classList.add('hidden');
    picker.classList.toggle('hidden');
}

function switchEmojiTab(category) {
    document.querySelectorAll('.emoji-tab').forEach(t => t.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
    loadEmojiCategory(category);
}

function loadEmojiCategory(category) {
    const grid = document.getElementById('emojiGrid');
    if (!grid) return;
    grid.innerHTML = '';
    
    let emojis = [];
    if (category === 'recent') {
        emojis = recentEmojis;
    } else if (category === 'custom') {
        Object.entries(customEmojis).forEach(([name, url]) => {
            const item = document.createElement('div');
            item.className = 'emoji-item';
            item.innerHTML = `<img src="${safeUrl(resolveUrl(url))}" alt="${escapeHtml(name)}" style="width: 28px; height: 28px;">`;
            item.onclick = () => insertEmoji(name);
            grid.appendChild(item);
        });
        return;
    } else {
        emojis = emojiCategories[category] || [];
    }
    
    emojis.forEach(emoji => {
        const item = document.createElement('div');
        item.className = 'emoji-item';
        item.textContent = emoji;
        item.onclick = () => insertEmoji(emoji);
        grid.appendChild(item);
    });
}

function insertEmoji(emoji) {
    const input = document.getElementById('messageInput');
    if (input) input.value += emoji;
    
    if (!recentEmojis.includes(emoji)) {
        recentEmojis.unshift(emoji);
        if (recentEmojis.length > 32) recentEmojis.pop();
        localStorage.setItem('recentEmojis', JSON.stringify(recentEmojis));
    }
}

function switchChannel(slug, onLoaded) {
    document.querySelectorAll('.channel').forEach(c => {
        c.classList.toggle('active', c.dataset.channel === slug);
    });
    currentChannel = slug;
    try { localStorage.setItem('lastChannel', currentChannel); } catch (e) {}

    const channelEl = document.getElementById('currentChannel');
    const welcomeEl = document.getElementById('welcomeChannel');
    const inputEl = document.getElementById('messageInput');

    if (channelEl) channelEl.textContent = currentChannel;
    if (welcomeEl) welcomeEl.textContent = currentChannel;
    if (inputEl) inputEl.placeholder = `Message #${currentChannel}`;

    const container = document.getElementById('messagesContainer');
    if (container) {
        container.innerHTML = `
            <div class="welcome-message">
                <h1>Welcome to #${currentChannel}!</h1>
                <p>Stay connected with your family 👨‍👩‍👧‍👦</p>
            </div>
        `;
    }

    if (socket) socket.emit('join', {room: currentChannel});

    fetch(apiUrl(`/api/messages?channel=${currentChannel}`))
        .then(r => r.json())
        .then(messages => {
            messages.forEach(msg => addMessage(msg));
            if (onLoaded) {
                // Jumping to a specific message (e.g. from search) — scroll
                // there first, then let the caller's own scroll-into-view
                // take over. Using the robust/image-aware scroll here could
                // yank the view back down to the bottom later if an image
                // above the target message finishes loading after we've
                // already landed on it.
                scrollToBottom();
                onLoaded();
            } else {
                scrollToBottomRobust();
            }
        });
}

function toggleSearch() {
    const modal = document.getElementById('searchModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    const input = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (input) { input.value = ''; input.focus(); }
    if (results) results.innerHTML = '<p class="hint">Type at least 2 characters and press Enter, or click Search.</p>';
}

function closeSearch() {
    const modal = document.getElementById('searchModal');
    if (modal) modal.classList.add('hidden');
}

function runSearch() {
    const input = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (!input || !results) return;
    const q = input.value.trim();
    if (q.length < 2) {
        results.innerHTML = '<p class="hint">Type at least 2 characters to search.</p>';
        return;
    }
    results.innerHTML = '<p class="hint">Searching…</p>';
    fetch(apiUrl(`/api/search?q=${encodeURIComponent(q)}`))
        .then(r => r.json())
        .then(matches => {
            if (!matches.length) {
                results.innerHTML = '<p class="hint">No messages found.</p>';
                return;
            }
            results.innerHTML = '';
            matches.forEach(m => {
                const item = document.createElement('div');
                item.className = 'search-result';
                const time = new Date(m.timestamp).toLocaleString();
                item.innerHTML = `
                    <div class="search-result-meta">${escapeHtml(m.channel_icon)} ${escapeHtml(m.channel_name)} · <strong>${escapeHtml(m.sender)}</strong> · ${escapeHtml(time)}</div>
                    <div class="search-result-content">${escapeHtml(m.content || '')}</div>
                `;
                item.onclick = () => jumpToSearchResult(m);
                results.appendChild(item);
            });
        })
        .catch(() => {
            results.innerHTML = '<p class="hint">Search failed — check the add-on log.</p>';
        });
}

function jumpToSearchResult(m) {
    closeSearch();
    switchChannel(m.channel, () => {
        const el = document.querySelector(`[data-id="${m.id}"]`);
        if (el) {
            el.scrollIntoView({behavior: 'smooth', block: 'center'});
            el.classList.add('highlight-flash');
            setTimeout(() => el.classList.remove('highlight-flash'), 2000);
        }
        // Older messages beyond the most recent 100 in a channel aren't
        // loaded yet — there's no "load more history" yet, so very old
        // results land you on the channel but won't auto-scroll to it.
    });
}

function openFileBrowser() {
    const modal = document.getElementById('filesModal');
    const list = document.getElementById('filesList');
    if (!modal || !list) return;
    modal.classList.remove('hidden');
    list.innerHTML = '<p class="hint">Loading…</p>';
    fetch(apiUrl(`/api/files?channel=${currentChannel}`))
        .then(r => r.json())
        .then(files => {
            if (!files.length) {
                list.innerHTML = '<p class="hint">No files shared in this channel yet.</p>';
                return;
            }
            list.innerHTML = '';
            files.forEach(f => {
                const item = document.createElement('a');
                item.className = 'file-browser-item';
                item.href = safeUrl(resolveUrl(f.url));
                item.target = '_blank';
                item.rel = 'noopener';
                const time = new Date(f.timestamp).toLocaleString();
                item.innerHTML = `
                    <div class="file-icon">${getFileIcon(f.mime_type)}</div>
                    <div class="file-info">
                        <div class="file-name">${escapeHtml(f.filename || 'file')}</div>
                        <div class="file-size">${escapeHtml(f.sender)} · ${formatFileSize(f.size || 0)} · ${escapeHtml(time)}</div>
                    </div>
                `;
                list.appendChild(item);
            });
        })
        .catch(() => {
            list.innerHTML = '<p class="hint">Failed to load files — check the add-on log.</p>';
        });
}

function closeFileBrowser() {
    const modal = document.getElementById('filesModal');
    if (modal) modal.classList.add('hidden');
}

function openEmojiManager() {
    const modal = document.getElementById('emojiModal');
    if (modal) modal.classList.remove('hidden');
    loadCustomEmojiList();
}

function closeEmojiManager() {
    const modal = document.getElementById('emojiModal');
    if (modal) modal.classList.add('hidden');
}

function openMySettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('hidden');

    fetch(apiUrl('/api/me'))
        .then(r => r.json())
        .then(me => {
            const input = document.getElementById('myAliasInput');
            const hint = document.getElementById('myHaNameHint');
            if (input) input.value = me.alias || '';
            if (hint) hint.textContent = `(your Home Assistant name is "${me.ha_name}")`;
        })
        .catch(() => {});
}

function closeMySettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('hidden');
}

function saveMyAlias() {
    const input = document.getElementById('myAliasInput');
    const alias = input ? input.value.trim() : '';

    fetch(apiUrl('/api/my-alias'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alias })
    })
        .then(r => r.json())
        .then(() => {
            // Reload so the new name applies everywhere at once — the
            // sidebar, the header, and every past message you've sent.
            location.reload();
        })
        .catch(() => {
            alert("Couldn't save your display name. Please try again.");
        });
}

function loadCustomEmojiList() {
    const list = document.getElementById('customEmojiList');
    if (!list) return;
    list.innerHTML = '';
    
    Object.entries(customEmojis).forEach(([name, url]) => {
        const item = document.createElement('div');
        item.className = 'custom-emoji-item';
        item.innerHTML = `
            <img src="${safeUrl(resolveUrl(url))}" alt="${escapeHtml(name)}">
            <span>${escapeHtml(name)}</span>
        `;
        list.appendChild(item);
    });
}

function uploadEmoji() {
    const nameInput = document.getElementById('newEmojiName');
    const fileInput = document.getElementById('emojiFileInput');
    
    if (!nameInput || !fileInput) return;
    
    const name = nameInput.value.trim();
    if (!name || !fileInput.files[0]) {
        alert('Please provide a name and image');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name.replace(/:/g, ''));
    formData.append('file', fileInput.files[0]);
    formData.append('created_by', currentUser || 'unknown');
    
    fetch(apiUrl('/api/emoji/upload'), {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            customEmojis[data.name] = data.url;
            loadCustomEmojiList();
            nameInput.value = '';
            fileInput.value = '';
        } else {
            alert(data.error);
        }
    });
}

function addReaction(messageId) {
    const emoji = prompt('Enter emoji:');
    if (emoji) {
        toggleReaction(messageId, emoji);
    }
}

function toggleReaction(messageId, emoji) {
    socket.emit('add_reaction', {
        message_id: messageId,
        emoji: emoji,
        user: currentUser
    });
}

function updateReaction(messageId, emoji, user) {
    // Refresh messages
}

function openImageViewer(url) {
    const viewer = document.getElementById('imageViewer');
    const img = document.getElementById('viewerImage');
    if (viewer && img) {
        img.src = url;
        viewer.classList.remove('hidden');
    }
}

function closeImageViewer() {
    const viewer = document.getElementById('imageViewer');
    if (viewer) viewer.classList.add('hidden');
}

function addToSharedMedia(url) {
    const grid = document.getElementById('sharedMedia');
    if (!grid) return;
    
    const safe = safeUrl(url);
    const item = document.createElement('div');
    item.className = 'media-item';
    item.innerHTML = `<img src="${safe}" onclick="openImageViewer('${safe}')" loading="lazy">`;
    grid.insertBefore(item, grid.firstChild);
}

// Close emoji picker when clicking outside
document.addEventListener('click', (e) => {
    const picker = document.getElementById('emojiPicker');
    const emojiBtn = document.querySelector('.emoji-btn');
    if (picker && emojiBtn && !picker.contains(e.target) && e.target !== emojiBtn && !picker.classList.contains('hidden')) {
        picker.classList.add('hidden');
    }
});

// --- GIF picker (GIPHY) ---
// The picker loads trending GIFs on first open, then re-queries as the
// person types (debounced). A monotonically increasing request id guards
// against an older, slower response overwriting a newer one if replies
// arrive out of order.
let gifSearchTimeout = null;
let gifRequestSeq = 0;

function toggleGifPicker() {
    const picker = document.getElementById('gifPicker');
    if (!picker) return;

    const emojiPicker = document.getElementById('emojiPicker');
    if (emojiPicker) emojiPicker.classList.add('hidden');

    const opening = picker.classList.contains('hidden');
    picker.classList.toggle('hidden');
    if (!opening) return;

    const input = document.getElementById('gifSearchInput');
    if (input && !input.dataset.bound) {
        input.dataset.bound = '1';
        input.addEventListener('input', onGifSearchInput);
        input.focus();
    }
    if (!picker.dataset.loaded) {
        picker.dataset.loaded = '1';
        fetchGifs('');
    }
}

function onGifSearchInput() {
    const input = document.getElementById('gifSearchInput');
    if (!input) return;
    clearTimeout(gifSearchTimeout);
    gifSearchTimeout = setTimeout(() => fetchGifs(input.value.trim()), 350);
}

function fetchGifs(query) {
    const grid = document.getElementById('gifGrid');
    if (!grid) return;
    const seq = ++gifRequestSeq;
    grid.innerHTML = '<div class="gif-picker-message">Loading…</div>';

    const endpoint = query ? `/api/giphy/search?q=${encodeURIComponent(query)}` : '/api/giphy/trending';
    fetch(apiUrl(endpoint))
        .then(r => r.json())
        .then(data => {
            if (seq !== gifRequestSeq) return; // superseded by a newer search
            if (data.error) {
                grid.innerHTML = `<div class="gif-picker-message">${escapeHtml(data.error)}</div>`;
                return;
            }
            renderGifGrid(data.gifs || []);
        })
        .catch(err => {
            if (seq !== gifRequestSeq) return;
            console.error('GIPHY fetch error:', err);
            grid.innerHTML = '<div class="gif-picker-message">Could not load GIFs.</div>';
        });
}

function renderGifGrid(gifs) {
    const grid = document.getElementById('gifGrid');
    if (!grid) return;
    grid.innerHTML = '';

    if (gifs.length === 0) {
        grid.innerHTML = '<div class="gif-picker-message">No GIFs found.</div>';
        return;
    }

    gifs.forEach(gif => {
        const item = document.createElement('div');
        item.className = 'gif-item';
        const img = document.createElement('img');
        img.src = safeUrl(gif.preview_url);
        img.alt = gif.title || 'GIF';
        img.loading = 'lazy';
        item.appendChild(img);
        item.onclick = () => sendGif(gif);
        grid.appendChild(item);
    });
}

function sendGif(gif) {
    const picker = document.getElementById('gifPicker');
    if (picker) picker.classList.add('hidden');

    // Sent straight over the socket, same as any other message — GIFs
    // reuse the existing file-message pipeline (image/gif mime type is
    // enough for the message list and shared-media panel to render it
    // like any other image), just with an external GIPHY URL instead of
    // an uploaded file.
    socket.emit('send_message', {
        sender: currentUser,
        content: '',
        channel: currentChannel,
        type: 'gif',
        file: {
            url: gif.url,
            filename: `${(gif.title || 'giphy').slice(0, 60)}.gif`,
            size: 0,
            mime_type: 'image/gif'
        }
    });
}

// Close GIF picker when clicking outside
document.addEventListener('click', (e) => {
    const picker = document.getElementById('gifPicker');
    const gifBtn = document.querySelector('.gif-btn');
    if (picker && gifBtn && !picker.contains(e.target) && e.target !== gifBtn && !picker.classList.contains('hidden')) {
        picker.classList.add('hidden');
    }
});
