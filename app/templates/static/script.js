let socket;
let currentUser = null;
let currentChannel = 'general';

// Check for saved user
if (localStorage.getItem('chatUser')) {
    currentUser = localStorage.getItem('chatUser');
    document.getElementById('userModal').classList.add('hidden');
    initializeChat();
} else {
    document.getElementById('userModal').classList.remove('hidden');
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
    });
    
    // Load existing messages
    fetch('/api/messages')
        .then(r => r.json())
        .then(messages => {
            messages.forEach(msg => addMessage(msg));
            scrollToBottom();
        });
    
    // Setup input
    const input = document.getElementById('messageInput');
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && this.value.trim()) {
            sendMessage(this.value.trim());
            this.value = '';
        }
    });
    
    // Channel switching
    document.querySelectorAll('.channel').forEach(ch => {
        ch.addEventListener('click', function() {
            document.querySelectorAll('.channel').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            currentChannel = this.dataset.channel;
            document.getElementById('currentChannel').textContent = currentChannel;
            document.getElementById('messageInput').placeholder = `Message #${currentChannel}`;
            
            // Clear and reload messages
            document.getElementById('messagesContainer').innerHTML = '';
            socket.emit('join', {room: currentChannel});
        });
    });
}

function sendMessage(content) {
    socket.emit('send_message', {
        sender: currentUser,
        content: content,
        channel: currentChannel
    });
}

function addMessage(data) {
    const container = document.getElementById('messagesContainer');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    const time = new Date(data.timestamp).toLocaleTimeString([], {
        hour: '2-digit', 
        minute: '2-digit'
    });
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${data.sender[0]}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${data.sender}</span>
                <span class="message-timestamp">${time}</span>
            </div>
            <div class="message-text">${escapeHtml(data.content)}</div>
        </div>
    `;
    
    container.appendChild(messageDiv);
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-scroll on new messages
const observer = new MutationObserver(() => {
    scrollToBottom();
});
