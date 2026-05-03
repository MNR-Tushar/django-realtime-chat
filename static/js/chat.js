// ── Elements ──────────────────────────────
const chatMessages   = document.getElementById('chatMessages');
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const statusEl       = document.getElementById('connectionStatus');
const typingEl       = document.getElementById('typingIndicator');
const toastContainer = document.getElementById('toastContainer');

// Optional elements — null check করা হবে use করার আগে
const attachBtn  = document.getElementById('attachBtn');
const uploadProg = document.getElementById('uploadProgress');
const notifBtn   = document.getElementById('notifBtn');

// ── WebSocket ─────────────────────────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${ROOM_SLUG}/`;
let socket;

function bindSocketEvents(ws) {
  ws.onopen = () => {
    statusEl.textContent = 'Connected';
    statusEl.className   = 'status connected';
    scrollToBottom();
  };
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected';
    statusEl.className   = 'status disconnected';
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
          document.title = `(${unreadCount}) ${ROOM_SLUG} — Django Chat`;
        }
      }
    }
    else if (data.type === 'user_join')    appendSystemMessage(`${data.username} joined`);
    else if (data.type === 'typing')       { if (data.username !== CURRENT_USER) typingEl.textContent = `${data.username} লেখতেছে...`; }
    else if (data.type === 'stop_typing')  typingEl.textContent = '';
    else if (data.type === 'online_count') document.getElementById('onlineCount').textContent = data.count;
    else if (data.type === 'message_read') {
      const el = document.querySelector(`[data-message-id="${data.message_id}"] .read-badge`);
      if (el) el.textContent = '✓✓';
    }
  };
}

function createSocket() {
  socket = new WebSocket(wsUrl);
  bindSocketEvents(socket);
}
createSocket();

// ── Text Message ──────────────────────────
function sendMessage() {
  const content = messageInput.value.trim();
  if (!content || !socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ message: content }));
  messageInput.value = '';
  messageInput.focus();
}

// ── File Upload ───────────────────────────
// FIX: <input type="file"> dynamically তৈরি করো — body তে append করে click।
// এতে room.html এ element না থাকলেও কাজ করবে,
// আর browser indirect .click() block করার সমস্যাও থাকবে না।
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
      showToast('Error', 'File size 10MB এর বেশি হবে না');
      return;
    }

    if (uploadProg) uploadProg.style.display = 'block';
    if (attachBtn)  attachBtn.disabled = true;

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
      showToast('Upload Error', err.message);
    } finally {
      if (uploadProg) uploadProg.style.display = 'none';
      if (attachBtn)  attachBtn.disabled = false;
    }
  });

  input.click();
}

if (attachBtn) {
  attachBtn.addEventListener('click', openFilePicker);
}

// ── Render ────────────────────────────────
function appendMessage({ content, username, timestamp, messageId, fileUrl, fileType, own }) {
  const div = document.createElement('div');
  div.className = `message ${own ? 'own' : ''}`;
  div.setAttribute('data-message-id', messageId);

  let bubbleInner = '';
  if (fileUrl) {
    if (fileType === 'image') {
      bubbleInner = `<img src="${fileUrl}" class="msg-image"
                       onclick="window.open(this.src)" alt="${escapeHtml(content)}">`;
    } else {
      bubbleInner = `<a href="${fileUrl}" class="msg-file" download>📎 ${escapeHtml(content)}</a>`;
    }
  } else {
    bubbleInner = escapeHtml(content);
  }

  div.innerHTML = `
    <div class="message-author">${escapeHtml(username)}</div>
    <div class="message-bubble">${bubbleInner}</div>
    <div class="message-footer">
      <span class="message-time">${timestamp}</span>
      ${own ? '<span class="read-badge">✓</span>' : ''}
    </div>`;
  chatMessages.appendChild(div);

  if (!own && socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'mark_as_read', message_id: messageId }));
  }
}

function appendSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'message system';
  div.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function scrollToBottom() { chatMessages.scrollTop = chatMessages.scrollHeight; }

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Toast ─────────────────────────────────
function showToast(title, body) {
  if (!toastContainer) return;
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerHTML = `<div class="toast-title">💬 ${escapeHtml(String(title))}</div>
                 <div class="toast-body">${escapeHtml(String(body))}</div>`;
  toastContainer.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ── Browser Notification ──────────────────
function showBrowserNotif(username, message) {
  if (!document.hidden || !('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;
  try {
    const n = new Notification(`💬 ${username}`, { body: message });
    n.onclick = () => { window.focus(); n.close(); };
  } catch (e) { /* ignore */ }
}

if (notifBtn) {
  if (Notification.permission === 'granted') {
    notifBtn.textContent = '🔔 Enabled';
    notifBtn.style.color = 'var(--green)';
  }
  notifBtn.addEventListener('click', async () => {
    if (!('Notification' in window)) { showToast('Info', 'এই browser এ notification নেই'); return; }
    const perm = await Notification.requestPermission();
    if (perm === 'granted') {
      notifBtn.textContent = '🔔 Enabled';
      notifBtn.style.color = 'var(--green)';
      showToast('Notification', 'চালু হয়েছে ✓');
    } else {
      showToast('Notification', 'Permission দেওয়া হয়নি');
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

let unreadCount = 0;
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) { unreadCount = 0; document.title = `${ROOM_SLUG} — Django Chat`; }
});

scrollToBottom();