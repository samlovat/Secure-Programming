// DOM elements
const chatMessages = document.getElementById('chatMessages');
const input = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');
const connectionStatus = document.getElementById('connectionStatus');
const chatTitle = document.getElementById('chatTitle');
const userList = document.getElementById('userList');
const groupList = document.getElementById('groupList');
const createGroupBtn = document.getElementById('createGroupBtn');
const groupForm = document.getElementById('groupForm');
const groupName = document.getElementById('groupName');
const groupMembers = document.getElementById('groupMembers');
const createGroupConfirm = document.getElementById('createGroupConfirm');
const createGroupCancel = document.getElementById('createGroupCancel');

// Application state
let currentChat = null;
let currentChatType = null; // 'user', 'group', 'public'
let onlineUsers = [];
let groups = [];
let currentUserId = null;

// WebSocket connection
const socket = new WebSocket('ws://localhost:8765');

// Helper function to add messages to chat
function addMessage(content, type = 'received', sender = null) {
    // Remove empty state if it exists
    const emptyState = chatMessages.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    if (sender && type === 'received') {
        const senderSpan = document.createElement('span');
        senderSpan.style.fontSize = '0.8rem';
        senderSpan.style.color = '#666';
        senderSpan.style.marginBottom = '4px';
        senderSpan.style.display = 'block';
        senderSpan.textContent = sender + ':';
        messageDiv.appendChild(senderSpan);
    }
    
    const contentSpan = document.createElement('span');
    contentSpan.textContent = content;
    messageDiv.appendChild(contentSpan);
    
    chatMessages.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Helper function to update connection status
function updateConnectionStatus(isConnected) {
    if (isConnected) {
        connectionStatus.classList.add('connected');
    } else {
        connectionStatus.classList.remove('connected');
    }
}

// Helper function to update user list
function updateUserList(users) {
    onlineUsers = users;
    userList.innerHTML = '';
    
    if (users.length === 0) {
        userList.innerHTML = '<div class="empty-state">No users online</div>';
        return;
    }
    
    users.forEach(user => {
        const userItem = document.createElement('div');
        userItem.className = 'user-item';
        userItem.dataset.userId = user;
        userItem.dataset.type = 'user';
        
        const avatar = document.createElement('div');
        avatar.className = 'user-avatar';
        avatar.textContent = user.charAt(0).toUpperCase();
        
        const info = document.createElement('div');
        info.className = 'user-info';
        
        const name = document.createElement('div');
        name.className = 'user-name';
        name.textContent = user;
        
        const status = document.createElement('div');
        status.className = 'user-status';
        status.textContent = 'Online';
        
        const indicator = document.createElement('div');
        indicator.className = 'online-indicator';
        
        info.appendChild(name);
        info.appendChild(status);
        userItem.appendChild(avatar);
        userItem.appendChild(info);
        userItem.appendChild(indicator);
        
        userItem.addEventListener('click', () => selectChat(user, 'user'));
        userList.appendChild(userItem);
    });
}

// Helper function to add group to list
function addGroupToList(groupId, groupName) {
    const groupItem = document.createElement('div');
    groupItem.className = 'group-item';
    groupItem.dataset.groupId = groupId;
    groupItem.dataset.type = 'group';
    
    const avatar = document.createElement('div');
    avatar.className = 'group-avatar';
    avatar.textContent = groupName.charAt(0).toUpperCase();
    
    const info = document.createElement('div');
    info.className = 'group-info';
    
    const name = document.createElement('div');
    name.className = 'group-name';
    name.textContent = groupName;
    
    info.appendChild(name);
    groupItem.appendChild(avatar);
    groupItem.appendChild(info);
    
    groupItem.addEventListener('click', () => selectChat(groupId, 'group'));
    groupList.appendChild(groupItem);
}

// Helper function to select a chat
function selectChat(targetId, type) {
    // Remove active class from all items
    document.querySelectorAll('.user-item, .group-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to selected item
    const selectedItem = document.querySelector(`[data-${type === 'user' ? 'user' : 'group'}Id="${targetId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    currentChat = targetId;
    currentChatType = type;
    
    // Update chat title
    if (type === 'user') {
        chatTitle.textContent = `Chat with ${targetId}`;
    } else if (type === 'group') {
        chatTitle.textContent = `Group: ${targetId}`;
    } else if (type === 'public') {
        chatTitle.textContent = 'Public Channel';
    }
    
    // Clear messages and show empty state
    chatMessages.innerHTML = '<div class="empty-state">No messages yet. Start the conversation!</div>';
    
    // Enable input
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
}

// Helper function to send different types of messages
function sendMessage() {
    const message = input.value.trim();
    if (!message || socket.readyState !== WebSocket.OPEN) return;
    
    if (currentChatType === 'user') {
        // Send direct message
        socket.send(JSON.stringify({
            type: 'CLIENT_COMMAND',
            payload: {
                cmd: `/tell ${currentChat} ${message}`
            }
        }));
        addMessage(message, 'sent');
    } else if (currentChatType === 'group') {
        // Send group message (placeholder - would need backend support)
        socket.send(JSON.stringify({
            type: 'CLIENT_COMMAND',
            payload: {
                cmd: `/group ${currentChat} ${message}`
            }
        }));
        addMessage(message, 'sent');
    } else if (currentChatType === 'public') {
        // Send public message
        socket.send(JSON.stringify({
            type: 'CLIENT_COMMAND',
            payload: {
                cmd: `/all ${message}`
            }
        }));
        addMessage(message, 'sent');
    }
    
    input.value = '';
}

// Helper function to create group
function createGroup() {
    const name = groupName.value.trim();
    const members = groupMembers.value.trim();
    
    if (!name) {
        alert('Please enter a group name');
        return;
    }
    
    // Send group creation command to server
    socket.send(JSON.stringify({
        type: 'CLIENT_COMMAND',
        payload: {
            cmd: `/create_group ${name} ${members}`
        }
    }));
    
    // Reset form
    groupName.value = '';
    groupMembers.value = '';
    groupForm.classList.remove('active');
    
    // Note: Group will be added to list and selected when server responds with GROUP_CREATED
}

// WebSocket event handlers
socket.onopen = () => {
    addMessage('Connected to chat server', 'system');
    updateConnectionStatus(true);
    sendBtn.disabled = false;
    
    // Request user list
    socket.send(JSON.stringify({
        type: 'CLIENT_COMMAND',
        payload: {
            cmd: '/list'
        }
    }));
};

socket.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'LIST') {
            updateUserList(data.payload.online || []);
        } else if (data.type === 'USER_DELIVER') {
            // Handle incoming messages
            const payload = data.payload;
            let messageContent = '';
            let sender = data.from || 'Unknown';
            
            // Try to decrypt message if it's encrypted
            if (payload.ciphertext) {
                // In a real implementation, you would decrypt here
                messageContent = '[Encrypted Message]';
            } else {
                messageContent = payload.text || payload.message || 'Unknown message format';
            }
            
            addMessage(messageContent, 'received', sender);
        } else if (data.type === 'ACK') {
            // Handle acknowledgments
            console.log('Received ACK:', data.payload);
        } else if (data.type === 'GROUP_CREATED') {
            // Handle group creation response
            const payload = data.payload;
            addGroupToList(payload.group_id, payload.group_name);
            addMessage(`Group "${payload.group_name}" created successfully!`, 'system');
            // Automatically select the new group
            selectChat(payload.group_id, 'group');
        } else {
            // Handle other message types
            addMessage(data.payload?.message || 'Unknown message', 'received');
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addMessage(event.data, 'received');
    }
};

socket.onclose = () => {
    addMessage('Connection closed', 'system');
    updateConnectionStatus(false);
    sendBtn.disabled = true;
    input.disabled = true;
};

socket.onerror = (error) => {
    addMessage('Connection error occurred', 'error');
    updateConnectionStatus(false);
    sendBtn.disabled = true;
    input.disabled = true;
};

// Event listeners
sendBtn.onclick = sendMessage;

input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Group creation event listeners
createGroupBtn.onclick = () => {
    groupForm.classList.toggle('active');
    if (groupForm.classList.contains('active')) {
        groupName.focus();
    }
};

createGroupConfirm.onclick = createGroup;

createGroupCancel.onclick = () => {
    groupForm.classList.remove('active');
    groupName.value = '';
    groupMembers.value = '';
};

// Initialize public channel selection
document.querySelector('[data-id="public"]').addEventListener('click', () => {
    selectChat('public', 'public');
});

// Focus input on load
window.addEventListener('load', () => {
    input.focus();
});

// Disable send button initially
sendBtn.disabled = true;
input.disabled = true;