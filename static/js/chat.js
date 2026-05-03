// ── Elements ──────────────────────────────
const chatMessages   = document.getElementById('chatMessages');
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const statusEl       = document.getElementById('connectionStatus');
const typingEl       = document.getElementById('typingIndicator');
const typingName     = document.getElementById('typingName');
const toastContainer = document.getElementById('toastContainer');
const attachBtn      = document.getElementById('attachBtn');
const uploadProg     = document.getElementById('uploadProgress');
const notifBtn       = document.getElementById('notifBtn');

// ── WebSocket ─────────────────────────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${ROOM_SLUG}/`;
let socket;

function bindSocketEvents(ws) {
  ws.onopen = () => {
    statusEl.textContent = 'Connected';
    statusEl.className   = 'status-badge connected';
    scrollToBottom();
  };
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected';
    statusEl.className   = 'status-badge disconnected';
    setTimeout(createSocket, 3000);
  };
  ws.onerror = (err) => console.error('WebSocket error:', err);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'chat_message') {
      appendMessage({
        content:   data.message,
        username:  data.username,
        timestamp: data.timestamp,
        messageId: data.message_id,
        fileUrl:   data.file_url  || null,
        fileType:  data.file_type || null,
        own:       data.username === CURRENT_USER,
      });
      scrollToBottom();
      if (data.username !== CURRENT_USER) {
        showToast(data.username, data.message);
        showBrowserNotif(data.username, data.message);
        if (document.hidden) {
          unreadCount++;
          document.title = `(${unreadCount}) #${ROOM_SLUG} — Nexus`;
        }
      }
    }
    else if (data.type === 'user_join') {
      appendSystemMessage(`${data.username} joined the channel`);
    }
    else if (data.type === 'typing') {
      if (data.username !== CURRENT_USER) {
        typingName.textContent = `${data.username} is typing…`;
        typingEl.style.display = 'flex';
      }
    }
    else if (data.type === 'stop_typing') {
      typingEl.style.display = 'none';
    }
    else if (data.type === 'online_count') {
      document.getElementById('onlineCount').textContent = data.count;
    }
    else if (data.type === 'message_read') {
      const row = document.querySelector(`[data-message-id="${data.message_id}"]`);
      if (row) {
        const tick = row.querySelector('.read-tick');
        if (tick) { tick.textContent = '✓✓'; tick.classList.add('seen'); }
      }
    }
  };
}

function createSocket() {
  socket = new WebSocket(wsUrl);
  bindSocketEvents(socket);
}
createSocket();

// ── Send Text ─────────────────────────────
function sendMessage() {
  const content = messageInput.value.trim();
  if (!content || !socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ message: content }));
  messageInput.value = '';
  messageInput.focus();
}

// ── File Upload ───────────────────────────
function openFilePicker() {
  const input = document.createElement('input');
  input.type   = 'file';
  input.accept = 'image/*,.pdf,.doc,.docx,.txt,.zip,.rar';
  input.style.cssText = 'position:fixed;top:-9999px;left:-9999px;';
  document.body.appendChild(input);

  input.addEventListener('change', async () => {
    const file = input.files[0];
    document.body.removeChild(input);
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      showToast('Error', 'File must be under 10 MB');
      return;
    }

    uploadProg.classList.add('active');
    uploadProg.style.display = 'flex';
    if (attachBtn) attachBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(UPLOAD_URL, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Upload failed');
      }
      const data = await res.json();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type:       'file_message',
          file_url:   data.url,
          file_type:  data.file_type,
          file_name:  file.name,
          message_id: data.id,
        }));
      }
    } catch (err) {
      showToast('Upload failed', err.message);
    } finally {
      uploadProg.style.display = 'none';
      uploadProg.classList.remove('active');
      if (attachBtn) attachBtn.disabled = false;
    }
  });

  input.click();
}

if (attachBtn) attachBtn.addEventListener('click', openFilePicker);

// ── Render Message ────────────────────────
function appendMessage({ content, username, timestamp, messageId, fileUrl, fileType, own }) {
  const row = document.createElement('div');
  row.className = `message-row ${own ? 'own' : ''}`;
  row.setAttribute('data-message-id', messageId);

  let bubbleInner = '';
  if (fileUrl) {
    if (fileType === 'image') {
      bubbleInner = `<img src="${fileUrl}" class="msg-image"
                       onclick="window.open(this.src)" alt="${escHtml(content)}">`;
    } else {
      bubbleInner = `
        <a href="${fileUrl}" class="msg-file" download>
          <div class="msg-file-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          ${escHtml(content)}
        </a>`;
    }
  } else {
    bubbleInner = escHtml(content);
  }

  const initials = username ? username[0].toUpperCase() : '?';

  row.innerHTML = `
    <div class="message-avatar">${initials}</div>
    <div class="message-col">
      <div class="message-name">${escHtml(username)}</div>
      <div class="message-bubble">${bubbleInner}</div>
      <div class="message-meta">
        <span class="message-time">${timestamp}</span>
        ${own ? '<span class="read-tick">✓</span>' : ''}
      </div>
    </div>`;

  chatMessages.appendChild(row);

  if (!own && socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'mark_as_read', message_id: messageId }));
  }
}

function appendSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'system-msg';
  div.innerHTML = `<span>${escHtml(text)}</span>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Toast ─────────────────────────────────
function showToast(title, body) {
  if (!toastContainer) return;
  const t = document.createElement('div');
  t.className = 'toast';
  const initials = title ? title[0].toUpperCase() : '?';
  t.innerHTML = `
    <div class="toast-header">
      <div class="toast-avatar">${initials}</div>
      <span class="toast-name">${escHtml(String(title))}</span>
    </div>
    <div class="toast-body">${escHtml(String(body))}</div>`;
  toastContainer.appendChild(t);
  setTimeout(() => {
    t.style.transition = 'opacity 0.2s, transform 0.2s';
    t.style.opacity = '0';
    t.style.transform = 'translateX(8px)';
    setTimeout(() => t.remove(), 200);
  }, 3800);
}

// ── Browser Notification ──────────────────
function showBrowserNotif(username, message) {
  if (!document.hidden || !('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;
  try {
    const n = new Notification(`${username}`, { body: message, icon: '/static/favicon.ico' });
    n.onclick = () => { window.focus(); n.close(); };
  } catch (e) {}
}

if (notifBtn) {
  if (Notification.permission === 'granted') {
    notifBtn.textContent = 'Notified';
    notifBtn.classList.add('enabled');
  }
  notifBtn.addEventListener('click', async () => {
    if (!('Notification' in window)) { showToast('Info', 'Notifications not supported'); return; }
    const perm = await Notification.requestPermission();
    if (perm === 'granted') {
      notifBtn.textContent = 'Notified';
      notifBtn.classList.add('enabled');
    }
  });
}

// ── Typing ────────────────────────────────
let typingTimer;
messageInput.addEventListener('input', () => {
  clearTimeout(typingTimer);
  if (socket && socket.readyState === WebSocket.OPEN)
    socket.send(JSON.stringify({ type: 'typing' }));
  typingTimer = setTimeout(() => {
    if (socket && socket.readyState === WebSocket.OPEN)
      socket.send(JSON.stringify({ type: 'stop_typing' }));
  }, 1500);
});

// ── Events ────────────────────────────────
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// ── Unread counter ────────────────────────
let unreadCount = 0;
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    unreadCount = 0;
    document.title = `#${ROOM_SLUG} — Nexus`;
  }
});

scrollToBottom();