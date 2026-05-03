// ── Elements ──────────────────────────────
const chatMessages   = document.getElementById('chatMessages');
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const statusEl       = document.getElementById('connectionStatus');
const typingEl       = document.getElementById('typingIndicator');



// ── WebSocket Connection ──────────────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${ROOM_SLUG}/`;
let socket;

function bindSocketEvents(ws) {
  ws.onopen = function() {
    console.log('WebSocket connected');
    statusEl.textContent = 'Connected';
    statusEl.className   = 'status connected';
    scrollToBottom();
  };

  ws.onclose = function() {
    console.log('WebSocket disconnected');
    statusEl.textContent = 'Disconnected';
    statusEl.className   = 'status disconnected';

    setTimeout(() => {
      console.log('Attempting to reconnect...');
      createSocket();
    }, 3000);
  };

  ws.onerror = function(err) {
    console.error('WebSocket error:', err);
  };

  ws.onmessage = function(event) {
    console.log('Message received:', event.data);
    const data = JSON.parse(event.data);

    if (data.type === 'chat_message') {
      console.log('Chat message from:', data.username);
      appendMessage({
        content:   data.message,
        username:  data.username,
        timestamp: data.timestamp,
        own:       data.username === CURRENT_USER,
      });
      scrollToBottom();
    }
    else if (data.type === 'user_join') {
      console.log('User joined:', data.username);
      appendSystemMessage(`${data.username} joined the room`);
    }
    else if (data.type === 'typing') {
      if (data.username !== CURRENT_USER) {
        typingEl.textContent = `${data.username} লেখতেছে...`;
      }
    }
    else if (data.type === 'stop_typing') {
      typingEl.textContent = '';
    }
  };
}

function createSocket() {
  console.log('Creating WebSocket to:', wsUrl);
  socket = new WebSocket(wsUrl);
  bindSocketEvents(socket);
}

createSocket();

// ── Send Message ──────────────────────────
function sendMessage() {
  const content = messageInput.value.trim();
  
  if (!content) {
    console.warn('Message is empty');
    return;
  }

  if (!socket) {
    console.error('Socket not initialized');
    return;
  }

  if (socket.readyState !== WebSocket.OPEN) {
    console.error(`Socket not ready. State: ${socket.readyState} (OPEN=${WebSocket.OPEN})`);
    return;
  }

  try {
    socket.send(JSON.stringify({ message: content }));
    console.log('Message sent:', content);
    messageInput.value = '';
    messageInput.focus();
  } catch (error) {
    console.error('Failed to send message:', error);
  }
}

// ── Render Functions ──────────────────────
function appendMessage({ content, username, timestamp, own }) {
  const div = document.createElement('div');
  div.className = `message ${own ? 'own' : ''}`;
  div.innerHTML = `
    <div class="message-author">${username}</div>
    <div class="message-bubble">${escapeHtml(content)}</div>
    <div class="message-time">${timestamp}</div>
  `;
  chatMessages.appendChild(div);
}

function appendSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'message system';
  div.innerHTML = `<div class="message-bubble">${text}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}


function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Typing Indicator ──────────────────────
let typingTimer;
messageInput.addEventListener('input', () => {
  clearTimeout(typingTimer);
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'typing', username: CURRENT_USER }));
  }
  typingTimer = setTimeout(() => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stop_typing' }));
    }
  }, 1500);
});

// ── Event Listeners ──────────────────────
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});


scrollToBottom();