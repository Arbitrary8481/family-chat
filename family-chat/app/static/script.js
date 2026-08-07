Here is the complete `script.js` code:

```javascript
// Global state
let socket;
let currentUser = null;
let currentChannel = 'general';
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

// Check for saved user
if (localStorage.getItem('chatUser')) {
    currentUser = localStorage.getItem('chatUser');
    document.getElementById('userModal').classList.add('hidden');
    initializeChat();
}

function selectUser(username) {
    currentUser = username;
    localStorage.setItem('chatUser', username);
    document.getElementById('userModal').classList.add('hidden');
    document.getElementById('currentUsername').textContent = username;
    document.getElementById('currentAvatar').textContent = username[0];
    initializeChat();
}

function initializeChat() {
    // Initialize Socket.IO
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        socket.emit('join', {room: currentChannel});
    });
    
    socket.on('new_message', function(data) {
        addMessage(data);
        scrollToBottom();
        
        // Add to shared media if image
        if (data.type === 'image' || (data.file && data.file.mime_type && data.file.mime_type.startsWith('image/'))) {
            addToSharedMedia(data.file.url);
        }
    });
    
    socket.on('reaction_added', function(data) {
        updateReaction(data.message_id, data.emoji, data.user);
    });
    
    // Load existing messages
    fetch('/api/messages')
        .then(r => r.json())
        .then(messages => {
            messages.forEach(msg => addMessage(msg));
            scrollToBottom();
        });
    
    // Load custom emojis
    fetch('/api/emojis')
        .then(r => r.json())
        .then(emojis => {
            customEmojis = emojis;
        });
    
    // Setup input
    const input = document.getElementById('messageInput');
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessageClick();
        }
    });
    
    // Channel switching
    document.querySelectorAll('.channel').forEach(ch => {
        ch.addEventListener('click', function() {
            document.querySelectorAll('.channel').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            currentChannel = this.dataset.channel;
            document.getElementById('currentChannel').textContent = currentChannel;
            document.getElementById('welcomeChannel').textContent = currentChannel;
            document.getElementById('messageInput').placeholder = `Message #${currentChannel}`;
            
            // Clear and reload messages
            document.getElementById('messagesContainer').innerHTML = `
                <div class="welcome-message">
                    <h1>Welcome to #${currentChannel}!</h1>
                    <p>Stay connected with your family 👨‍👩‍👧‍👦</p>
                </div>
            `;
            socket.emit('join', {room: currentChannel});
            
            fetch(`/api/messages?channel=${currentChannel}`)
                .then(r => r.json())
                .then(messages => {
                    messages.forEach(msg => addMessage(msg));
                    scrollToBottom();
                });
        });
    });
    
    // Initialize emoji picker
    loadEmojiCategory('people');
}

function sendMessageClick() {
    const input = document.getElementById('messageInput');
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
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.dataset.id = data.id;
    
    const time = new Date(data.timestamp).toLocaleTimeString([], {
        hour: '2-digit', 
        minute: '2-digit'
    });
    
    // Determine avatar color based on sender
    const isUser1 = data.sender === document.querySelector('.user-option:first-child span')?.textContent;
    const avatarStyle = isUser1 ? 
        'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);' : 
        'background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);';
    
    let contentHtml = `<div class="message-text">${escapeHtml(data.content || '')}</div>`;
    
    // Handle file attachments
    if (data.file || data.file_url) {
        const fileUrl = data.file?.url || data.file_url;
        const fileName = data.file?.filename || data.file_name;
        const mimeType = data.file?.mime_type || data.mime_type;
        
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
                            <div class="file-name">${escapeHtml(fileName)}</div>
                            <div class="file-size">${fileSize}</div>
                        </div>
                    </a>
                </div>
            `;
        }
    }
    
    // Reactions
    let reactionsHtml = '';
    if (data.reactions && Object.keys(data.reactions).length > 0) {
        reactionsHtml = '<div class="message-reactions">';
        for (const [emoji, users] of Object.entries(data.reactions)) {
            const isActive = users.includes(currentUser);
            reactionsHtml += `
                <div class="reaction ${isActive ? 'active' : ''}" onclick="toggleReaction(${data.id}, '${emoji}')">
                    ${emoji} <span class="reaction-count">${users.length}</span>
                </div>
            `;
        }
        reactionsHtml += '</div>';
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar" style="${avatarStyle}">${data.sender[0]}</div>
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
            <button class="action-btn" title="Reply">↩️</button>
            <button class="action-btn" title="More">⋯</button>
        </div>
    `;
    
    container.appendChild(messageDiv);
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

// File Upload
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    fetch('/api/upload', {
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
    
    if (data.mime_type.startsWith('image/')) {
        content.innerHTML = `<img src="${data.url}" alt="${data.filename}">`;
    } else if (data.mime_type.startsWith('video/')) {
        content.innerHTML = `
            <video controls>
                <source src="${data.url}" type="${data.mime_type}">
            </video>
        `;
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
    document.getElementById('fileModal').classList.add('hidden');
    selectedFile = null;
}

function sendFile() {
    const caption = document.getElementById('fileCaption').value;
    sendMessage(caption);
}

// Emoji Picker
function toggleEmojiPicker() {
    const picker = document.getElementById('emojiPicker');
    picker.classList.toggle('hidden');
}

function switchEmojiTab(category) {
    document.querySelectorAll('.emoji-tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    loadEmojiCategory(category);
}

function loadEmojiCategory(category) {
    const grid = document.getElementById('emojiGrid');
    grid.innerHTML = '';
    
    let emojis = [];
    if (category === 'recent') {
        emojis = recentEmojis;
    } else if (category === 'custom') {
        // Load custom emojis
        Object.entries(customEmojis).forEach(([name, url]) => {
            const item = document.createElement('div');
            item.className = 'emoji-item';
            item.innerHTML = `<img src="${url}" alt="${name}" style="width: 28px; height: 28px;">`;
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
    input.value += emoji;
    input.focus();
    
    // Add to recent
    if (!recentEmojis.includes(emoji)) {
        recentEmojis.unshift(emoji);
        if (recentEmojis.length > 32) recentEmojis.pop();
        localStorage.setItem('recentEmojis', JSON.stringify(recentEmojis));
    }
}

// Custom Emoji Manager
function openEmojiManager() {
    document.getElementById('emojiModal').classList.remove('hidden');
    loadCustomEmojiList();
}

function closeEmojiManager() {
    document.getElementById('emojiModal').classList.add('hidden');
}

function loadCustomEmojiList() {
    const list = document.getElementById('customEmojiList');
    list.innerHTML = '';
    
    Object.entries(customEmojis).forEach(([name, url]) => {
        const item = document.createElement('div');
        item.className = 'custom-emoji-item';
        item.innerHTML = `
            <img src="${url}" alt="${name}">
            <span>${name}</span>
        `;
        list.appendChild(item);
    });
}

function uploadEmoji() {
    const name = document.getElementById('newEmojiName').value.trim();
    const fileInput = document.getElementById('emojiFileInput');
    
    if (!name || !fileInput.files[0]) {
        alert('Please provide a name and image');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name.replace(/:/g, ''));
    formData.append('file', fileInput.files[0]);
    formData.append('created_by', currentUser);
    
    fetch('/api/emoji/upload', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            customEmojis[data.name] = `/uploads/emoji_${name}_${Date.now()}.png`;
            loadCustomEmojiList();
            document.getElementById('newEmojiName').value = '';
            fileInput.value = '';
        } else {
            alert(data.error);
        }
    });
}

// Reactions
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
    // Refresh messages to show updated reactions
    // In a real app, you'd update just the reaction element
}

// Image Viewer
function openImageViewer(url) {
    const viewer = document.getElementById('imageViewer');
    const img = document.getElementById('viewerImage');
    img.src = url;
    viewer.classList.remove('hidden');
}

function closeImageViewer() {
    document.getElementById('imageViewer').classList.add('hidden');
}

// Shared Media
function addToSharedMedia(url) {
    const grid = document.getElementById('sharedMedia');
    const item = document.createElement('div');
    item.className = 'media-item';
    item.innerHTML = `<img src="${url}" onclick="openImageViewer('${url}')" loading="lazy">`;
    grid.insertBefore(item, grid.firstChild);
}

// Close emoji picker when clicking outside
document.addEventListener('click', (e) => {
    const picker = document.getElementById('emojiPicker');
    const emojiBtn = document.querySelector('.emoji-btn');
    if (!picker.contains(e.target) && e.target !== emojiBtn && !picker.classList.contains('hidden')) {
        picker.classList.add('hidden');
    }
});
```
