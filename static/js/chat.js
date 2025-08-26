// Initialize Socket.IO connection
const socket = io();

// Get DOM elements
const messagesContainer = document.getElementById('messages');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const userCountElement = document.getElementById('user-count');

// Get room and user info from hidden inputs
const roomId = document.getElementById('room-id').value;
const username = document.getElementById('username').value;

// Join the room when page loads
socket.emit('join', {room_id: parseInt(roomId)});

// Handle form submission
messageForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (message === '') return;
    
    // Disable send button temporarily
    sendBtn.disabled = true;
    
    // Send message
    socket.emit('message', {
        message: message,
        room_id: parseInt(roomId)
    });
    
    // Clear input
    messageInput.value = '';
    
    // Re-enable send button
    setTimeout(() => {
        sendBtn.disabled = false;
        messageInput.focus();
    }, 100);
});

// Handle incoming messages
socket.on('message', function(data) {
    addMessage(data.username, data.message, data.timestamp, false);
});

// Handle status messages (join/leave notifications)
socket.on('status', function(data) {
    addMessage('System', data.msg, data.timestamp, true);
});

// Handle user count updates
socket.on('user_count', function(data) {
    const count = data.count;
    const text = count === 1 ? '1 user online' : `${count} users online`;
    userCountElement.textContent = text;
});

// Function to add message to chat
function addMessage(username, message, timestamp, isStatus = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message mb-2 new-message${isStatus ? ' status-message' : ''}`;
    
    messageDiv.innerHTML = `
        <strong class="username">${escapeHtml(username)}:</strong>
        <span class="message-content">${escapeHtml(message)}</span>
        <small class="text-muted timestamp">${timestamp}</small>
    `;
    
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Remove animation class after animation completes
    setTimeout(() => {
        messageDiv.classList.remove('new-message');
    }, 300);
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Handle page visibility change
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        messageInput.focus();
    }
});

// Focus on message input when page loads
window.addEventListener('load', function() {
    messageInput.focus();
});

// Handle browser back/forward buttons
window.addEventListener('beforeunload', function() {
    socket.emit('leave', {room_id: parseInt(roomId)});
});

// Handle Enter key for sending messages
messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        messageForm.dispatchEvent(new Event('submit'));
    }
});

// Handle connection status
socket.on('connect', function() {
    console.log('Connected to server');
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
    addMessage('System', 'Connection lost. Trying to reconnect...', new Date().toLocaleTimeString(), true);
});

socket.on('connect_error', function(error) {
    console.error('Connection error:', error);
    addMessage('System', 'Connection error. Please refresh the page.', new Date().toLocaleTimeString(), true);
});