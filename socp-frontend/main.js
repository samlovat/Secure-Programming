const log = document.getElementById('log');
const input = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');

// Change the URL if your backend runs elsewhere
const socket = new WebSocket('ws://localhost:8765');

socket.onopen = () => {
    log.textContent += 'Connected to WebSocket server\n';
};

socket.onmessage = (event) => {
    log.textContent += 'Received: ' + event.data + '\n';
};

socket.onclose = () => {
    log.textContent += 'Connection closed\n';
};

socket.onerror = (error) => {
    log.textContent += 'WebSocket error\n';
};

sendBtn.onclick = () => {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(input.value);
        log.textContent += 'Sent: ' + input.value + '\n';
        input.value = '';
    }
};