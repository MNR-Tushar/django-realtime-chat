/* ═══════════════════════════════════════════════
   TELEGRAM-STYLE CHAT.JS
   Features: Emoji picker, Reactions, Sound,
             Dark/Light mode, User sidebar,
             Auto-resize textarea,
             Message Edit + Delete,
             Message Reply (quoted),
             Message Search with highlight
═══════════════════════════════════════════════ */

// ── DOM Elements ──────────────────────────────
const chatMessages   = document.getElementById('chatMessages');
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const statusEl       = document.getElementById('connectionStatus');
const typingEl       = document.getElementById('typingIndicator');
const toastContainer = document.getElementById('toastContainer');
const attachBtn      = document.getElementById('attachBtn');
const emojiBtn       = document.getElementById('emojiBtn');
const uploadProg     = document.getElementById('uploadProgress');
const themeBtn       = document.getElementById('themeBtn');
const soundBtn       = document.getElementById('soundBtn');
const usersSidebarEl = document.getElementById('usersSidebar');
const usersBtn       = document.getElementById('usersBtn');
const onlineCountEl  = document.getElementById('onlineCount');
const editBar        = document.getElementById('editBar');
const replyBar       = document.getElementById('replyBar');
const replyBarLabel  = document.getElementById('replyBarLabel');
const replyBarText   = document.getElementById('replyBarText');

// Search elements
const searchBtn    = document.getElementById('searchBtn');
const searchPanel  = document.getElementById('searchPanel');
const searchInput  = document.getElementById('searchInput');
const searchCount  = document.getElementById('searchCount');
const searchPrev   = document.getElementById('searchPrev');
const searchNext   = document.getElementById('searchNext');
const searchClose  = document.getElementById('searchClose');

// ── State ─────────────────────────────────────
let socket;
let unreadCount   = 0;
let soundEnabled  = true;
let emojiPickerOpen = false;
let reactionPickerTarget = null;
let currentReactionPicker = null;
const messageReactions = typeof INITIAL_REACTIONS !== 'undefined' ? INITIAL_REACTIONS : {};

// Edit state
let editingMessageId = null;

// Delete state
let pendingDeleteId = null;

// Reply state
let replyingToId       = null;
let replyingToUsername = null;
let replyingToText     = null;

// Search state
let searchResults  = [];   // [{msgEl, textNode, start, end}] — one entry per match
let searchCurrent  = -1;   // index into searchResults

// Pagination state
let isLoadingOlder = false;
let hasMoreMessages = true;
let oldestMessageId = null;

// ── Message Pagination ────────────────────────
function initPagination() {
  // Find the oldest message ID from the initial load
  const firstMsg = chatMessages.querySelector('.message[data-message-id]');
  if (firstMsg) {
    oldestMessageId = parseInt(firstMsg.dataset.messageId);
  }

  // Add scroll listener
  chatMessages.addEventListener('scroll', handleScroll);
}

function handleScroll() {
  if (isLoadingOlder || !hasMoreMessages) return;

  // Check if scrolled near the top (within 100px)
  if (chatMessages.scrollTop < 100) {
    loadOlderMessages();
  }
}

function showLoadingIndicator() {
  let loader = document.getElementById('paginationLoader');
  if (!loader) {
    loader = document.createElement('div');
    loader.id = 'paginationLoader';
    loader.innerHTML = `
      <div style="text-align:center;padding:16px;color:var(--muted);font-size:12px;">
        <span class="typing-dots"><span></span><span></span><span></span></span>
        Loading older messages...
      </div>
    `;
    chatMessages.insertBefore(loader, chatMessages.firstChild);
  }
  loader.style.display = 'block';
}

function hideLoadingIndicator() {
  const loader = document.getElementById('paginationLoader');
  if (loader) loader.style.display = 'none';
}

async function loadOlderMessages() {
  if (!oldestMessageId || !window.OLDER_MESSAGES_URL) return;

  isLoadingOlder = true;
  showLoadingIndicator();

  try {
    const url = `${window.OLDER_MESSAGES_URL}?before_id=${oldestMessageId}`;
    const res = await fetch(url, {
      headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' }
    });

    if (!res.ok) {
      hideLoadingIndicator();
      isLoadingOlder = false;
      return;
    }

    const data = await res.json();

    if (data.messages && data.messages.length > 0) {
      // Remember current scroll position
      const oldHeight = chatMessages.scrollHeight;
      const oldScrollTop = chatMessages.scrollTop;

      // Prepend messages (they come in chronological order)
      data.messages.forEach(msg => {
        prependMessage({
          content: msg.content,
          username: msg.author,
          timestamp: msg.timestamp,
          messageId: msg.id,
          fileUrl: msg.file_url || null,
          fileType: msg.file_type || null,
          replyTo: msg.reply_to || null,
          own: msg.is_own,
          isEdited: msg.is_edited,
        });
      });

      // Update oldest message ID
      oldestMessageId = data.messages[0].id;

      // Maintain scroll position
      const newHeight = chatMessages.scrollHeight;
      chatMessages.scrollTop = newHeight - oldHeight + oldScrollTop;

      hasMoreMessages = data.has_more;
    } else {
      hasMoreMessages = false;
    }

    if (!hasMoreMessages) {
      showNoMoreMessages();
    }
  } catch (err) {
    console.error('Failed to load older messages:', err);
  } finally {
    hideLoadingIndicator();
    isLoadingOlder = false;
  }
}

function showNoMoreMessages() {
  let noMore = document.getElementById('noMoreMessages');
  if (!noMore) {
    noMore = document.createElement('div');
    noMore.id = 'noMoreMessages';
    noMore.style.cssText = 'text-align:center;padding:12px;color:var(--muted);font-size:11px;';
    noMore.textContent = 'No more messages';
    chatMessages.insertBefore(noMore, chatMessages.firstChild);
  }
}

function prependMessage({ content, username, timestamp, messageId, fileUrl, fileType, replyTo, own, isEdited }) {
  const isGrouped = username === lastAuthor && !replyTo;

  const div = document.createElement('div');
  div.className = `message ${own ? 'own' : ''} ${isGrouped ? 'grouped' : ''}`;
  div.setAttribute('data-message-id', messageId);
  div.setAttribute('data-is-own', own ? 'true' : 'false');

  // Reply quote HTML
  let replyHtml = '';
  if (replyTo) {
    const safeUser = escapeHtml(replyTo.username);
    const safeText = escapeHtml(replyTo.text.substring(0, 80));
    replyHtml = `
      <div class="reply-quote" onclick="scrollToMessage(${replyTo.id})">
        <span class="reply-quote-author">↩ ${safeUser}</span>
        <span class="reply-quote-text">${safeText}</span>
      </div>`;
  }

  let bubbleInner = '';
  if (fileUrl) {
    if (fileType === 'image') {
      bubbleInner = `<img src="${fileUrl}" class="msg-image"
                       onclick="window.open(this.src)" alt="${escapeHtml(content)}">`;
    } else {
      bubbleInner = `<a href="${fileUrl}" class="msg-file" download>📎 ${escapeHtml(content)}</a>`;
    }
  } else {
    bubbleInner = `<span class="msg-text">${escapeHtml(content)}</span>`;
  }

  const editedBadge = isEdited ? '<span class="edited-badge">edited</span>' : '';

  const replyAction = `<button class="msg-action-btn reply-btn"
      onclick="startReply('${messageId}', '${escapeHtml(username)}', this)"
      title="Reply">↩</button>`;

  const ownActions = own ? `
    ${!fileUrl ? `<button class="msg-action-btn edit-btn"
        onclick="startEdit('${messageId}')" title="Edit">✏️</button>` : ''}
    <button class="msg-action-btn delete-btn"
        onclick="confirmDelete('${messageId}')" title="Delete">🗑️</button>` : '';

  div.innerHTML = `
    <div class="message-author">${escapeHtml(username)}</div>
    <div class="message-bubble">
      ${replyHtml}
      ${bubbleInner}
      <span class="reaction-trigger" title="Add reaction">😊</span>
    </div>
    <div class="message-footer">
      <span class="message-time">${timestamp}</span>
      ${editedBadge}
      ${own ? '<span class="read-badge">✓</span>' : ''}
      <span class="msg-actions">
        ${replyAction}
        ${ownActions}
      </span>
    </div>
  `;

  // Reaction trigger
  const trigger = div.querySelector('.reaction-trigger');
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    showReactionPicker(trigger, messageId);
  });

  // Insert at the beginning (after the date divider)
  const dateDivider = chatMessages.querySelector('.date-divider');
  if (dateDivider) {
    dateDivider.after(div);
  } else {
    chatMessages.insertBefore(div, chatMessages.firstChild);
  }

  lastAuthor = username;
}

// ── Theme ─────────────────────────────────────
const savedTheme = localStorage.getItem('chat-theme') || 'dark';
if (savedTheme === 'light') document.body.classList.add('light-mode');
updateThemeBtn();

function updateThemeBtn() {
  if (themeBtn) {
    const isLight = document.body.classList.contains('light-mode');
    themeBtn.textContent = isLight ? '☀️' : '🌙';
    themeBtn.title = isLight ? 'Switch to Dark Mode' : 'Switch to Light Mode';
  }
}

if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    document.body.classList.toggle('light-mode');
    const theme = document.body.classList.contains('light-mode') ? 'light' : 'dark';
    localStorage.setItem('chat-theme', theme);
    updateThemeBtn();
    showToast('Theme', theme === 'light' ? '☀️ Light mode on' : '🌙 Dark mode on');
  });
}

// ── Sound ─────────────────────────────────────
function createBeep(type = 'receive') {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    if (type === 'receive') {
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.08);
    } else {
      osc.frequency.setValueAtTime(660, ctx.currentTime);
      osc.frequency.setValueAtTime(880, ctx.currentTime + 0.06);
    }
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.22);
  } catch (e) { /* AudioContext not available */ }
}

function playSound(type) {
  if (!soundEnabled) return;
  createBeep(type);
}

if (soundBtn) {
  soundEnabled = localStorage.getItem('chat-sound') !== 'off';
  updateSoundBtn();
  soundBtn.addEventListener('click', () => {
    soundEnabled = !soundEnabled;
    localStorage.setItem('chat-sound', soundEnabled ? 'on' : 'off');
    updateSoundBtn();
    showToast('Sound', soundEnabled ? '🔊 Sound on' : '🔇 Sound off');
  });
}

function updateSoundBtn() {
  if (!soundBtn) return;
  soundBtn.textContent = soundEnabled ? '🔊' : '🔇';
  soundBtn.title = soundEnabled ? 'Mute sounds' : 'Enable sounds';
}

// ── Users Sidebar Toggle ──────────────────────
if (usersBtn && usersSidebarEl) {
  usersBtn.addEventListener('click', () => {
    usersSidebarEl.classList.toggle('collapsed');
    usersBtn.classList.toggle('active');
  });
}

// ════════════════════════════════════════════
//  MESSAGE SEARCH
// ════════════════════════════════════════════

if (searchBtn) {
  searchBtn.addEventListener('click', openSearch);
}
if (searchClose) {
  searchClose.addEventListener('click', closeSearch);
}
if (searchInput) {
  searchInput.addEventListener('input', runSearch);
}
if (searchPrev) {
  searchPrev.addEventListener('click', () => navigateSearch(-1));
}
if (searchNext) {
  searchNext.addEventListener('click', () => navigateSearch(1));
}

// Ctrl+F / Cmd+F shortcut
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    e.preventDefault();
    if (searchPanel && searchPanel.classList.contains('open')) {
      closeSearch();
    } else {
      openSearch();
    }
  }
  if (e.key === 'Escape') {
    if (searchPanel && searchPanel.classList.contains('open')) {
      closeSearch();
    }
    document.getElementById('deleteModal').style.display = 'none';
    pendingDeleteId = null;
    if (editingMessageId) cancelEdit();
    if (replyingToId) cancelReply();
  }
});

function openSearch() {
  if (!searchPanel) return;
  searchPanel.classList.add('open');
  searchInput.focus();
  if (searchBtn) searchBtn.classList.add('active');
}

function closeSearch() {
  if (!searchPanel) return;
  searchPanel.classList.remove('open');
  clearSearchHighlights();
  searchResults = [];
  searchCurrent = -1;
  updateSearchCount();
  if (searchBtn) searchBtn.classList.remove('active');
}

function runSearch() {
  clearSearchHighlights();
  searchResults = [];
  searchCurrent = -1;

  const query = searchInput.value.trim();
  if (!query) {
    updateSearchCount();
    return;
  }

  // Search through all .msg-text spans
  const textSpans = chatMessages.querySelectorAll('.msg-text');
  const re = new RegExp(escapeRegex(query), 'gi');

  textSpans.forEach(span => {
    const msgEl = span.closest('.message');
    if (!msgEl) return;

    const originalText = span.textContent;
    let match;
    const matches = [];
    re.lastIndex = 0;
    while ((match = re.exec(originalText)) !== null) {
      matches.push({ start: match.index, end: match.index + match[0].length });
    }
    if (!matches.length) return;

    // Rebuild span HTML with <mark> tags
    let html = '';
    let cursor = 0;
    matches.forEach((m, i) => {
      html += escapeHtml(originalText.slice(cursor, m.start));
      html += `<mark class="search-highlight" data-match-idx="${searchResults.length + i}">${escapeHtml(originalText.slice(m.start, m.end))}</mark>`;
      cursor = m.end;
      searchResults.push({ msgEl, span });
    });
    html += escapeHtml(originalText.slice(cursor));
    span.innerHTML = html;
  });

  if (searchResults.length > 0) {
    searchCurrent = 0;
    highlightCurrent();
  }
  updateSearchCount();
}

function navigateSearch(dir) {
  if (!searchResults.length) return;
  searchCurrent = (searchCurrent + dir + searchResults.length) % searchResults.length;
  highlightCurrent();
  updateSearchCount();
}

function highlightCurrent() {
  // Remove .current from all
  chatMessages.querySelectorAll('.search-highlight.current').forEach(el => {
    el.classList.remove('current');
  });

  const entry = searchResults[searchCurrent];
  if (!entry) return;

  // Mark the current highlight element
  const mark = entry.span.querySelector(`[data-match-idx="${searchCurrent}"]`);
  if (mark) {
    mark.classList.add('current');
    entry.msgEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    // Briefly outline the message bubble
    entry.msgEl.classList.add('search-target');
    setTimeout(() => entry.msgEl.classList.remove('search-target'), 1200);
  }
}

function clearSearchHighlights() {
  // Restore all msg-text spans to plain text
  chatMessages.querySelectorAll('.msg-text').forEach(span => {
    const marks = span.querySelectorAll('.search-highlight');
    if (marks.length) {
      // Flatten innerHTML back to text
      span.textContent = span.textContent; // browser strips tags
    }
  });
}

function updateSearchCount() {
  if (!searchCount) return;
  if (!searchResults.length) {
    searchCount.textContent = searchInput && searchInput.value.trim() ? '0 results' : '';
    if (searchPrev) searchPrev.disabled = true;
    if (searchNext) searchNext.disabled = true;
    return;
  }
  searchCount.textContent = `${searchCurrent + 1} / ${searchResults.length}`;
  if (searchPrev) searchPrev.disabled = searchResults.length <= 1;
  if (searchNext) searchNext.disabled = searchResults.length <= 1;
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ════════════════════════════════════════════
//  REPLY
// ════════════════════════════════════════════

function startReply(messageId, username, btnEl) {
  // Get the text content from the message bubble
  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  let text = '';
  if (msgEl) {
    const textSpan = msgEl.querySelector('.msg-text');
    const fileEl   = msgEl.querySelector('.msg-file, .msg-image');
    if (textSpan)  text = textSpan.textContent.trim();
    else if (fileEl) text = '📎 File';
  }

  replyingToId       = messageId;
  replyingToUsername = username;
  replyingToText     = text;

  if (replyBar) {
    replyBarLabel.textContent = `↩ Replying to ${username}`;
    replyBarText.textContent  = text.substring(0, 100) || '…';
    replyBar.style.display    = 'flex';
  }

  messageInput.focus();
}

function cancelReply() {
  replyingToId       = null;
  replyingToUsername = null;
  replyingToText     = null;
  if (replyBar) replyBar.style.display = 'none';
}

// Scroll to a replied-to message (used when clicking the quote bubble)
function scrollToMessage(messageId) {
  const el = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  // Flash effect
  el.classList.add('search-target');
  setTimeout(() => el.classList.remove('search-target'), 1200);
}

// ── Emoji Picker ──────────────────────────────
const EMOJI_CATEGORIES = {
  '😊': ['😀','😁','😂','🤣','😊','😇','🙂','😉','😍','🥰','😘','😋','😎','🤩','😏','😒','😔','😢','😭','😤','😡','🤬','😱','😨','😰','🤗','🤔','🙄','😴','🤧','🥺','😠','🥳','🤪','😜','😝','😛','🤑','🤠'],
  '👍': ['👍','👎','👏','🙌','🤝','🤜','🤛','✊','👊','🤚','✋','🖐','👋','🤙','💪','🦵','🦶','👂','👃','🧠','🫀','🫁','🦷','🦴','👀','👁','👅','👄','💋','🤲','🤜','🤛'],
  '❤️': ['❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔','❣️','💕','💞','💓','💗','💖','💘','💝','💟','☮️','✝️','☯️','🔥','⭐','✨','💫','⚡','🌟','🌈','☀️','🌙','🌊','🌸','🌺','🌹','🌻','🌼','🌷'],
  '🎉': ['🎉','🎊','🎈','🎁','🎀','🎗','🎟','🎫','🏆','🥇','🥈','🥉','🎖','🎗','🏅','🎯','🎮','🎲','🎳','🎰','🎭','🎨','🎬','🎤','🎧','🎵','🎶','🎷','🎸','🎹','🎺','🎻','🥁'],
  '🐶': ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🙈','🙉','🙊','🐔','🐧','🐦','🦆','🦅','🦉','🦇','🐺','🐗','🦄','🐝','🦋','🐛','🐌','🐞'],
  '🍕': ['🍕','🍔','🌮','🌯','🥪','🍟','🌭','🍿','🧆','🥚','🍳','🥞','🧇','🥓','🥩','🍗','🍖','🦴','🌮','🍣','🍱','🍜','🍝','🍛','🍲','🥘','🫕','🥣','🥗','🧂'],
};

let currentEmojiCategory = '😊';
let emojiSearchQuery = '';

function createEmojiPicker() {
  const picker = document.createElement('div');
  picker.className = 'emoji-picker';
  picker.id = 'emojiPicker';

  const tabs = Object.keys(EMOJI_CATEGORIES).map(cat =>
    `<button class="emoji-tab ${cat === currentEmojiCategory ? 'active' : ''}" data-cat="${cat}">${cat}</button>`
  ).join('');

  picker.innerHTML = `
    <div class="emoji-picker-tabs">${tabs}</div>
    <div class="emoji-search">
      <input type="text" placeholder="Search emoji..." id="emojiSearch" value="${emojiSearchQuery}">
    </div>
    <div class="emoji-grid" id="emojiGrid"></div>
  `;

  document.querySelector('.chat-input-area')?.parentElement?.appendChild(picker);
  renderEmojiGrid(picker);

  picker.querySelectorAll('.emoji-tab').forEach(btn => {
    btn.addEventListener('click', (e) => {
      currentEmojiCategory = e.target.dataset.cat;
      picker.querySelectorAll('.emoji-tab').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      emojiSearchQuery = '';
      picker.querySelector('#emojiSearch').value = '';
      renderEmojiGrid(picker);
    });
  });

  picker.querySelector('#emojiSearch').addEventListener('input', (e) => {
    emojiSearchQuery = e.target.value;
    renderEmojiGrid(picker);
  });

  return picker;
}

function renderEmojiGrid(picker) {
  const grid = picker.querySelector('#emojiGrid');
  const filtered = emojiSearchQuery
    ? Object.values(EMOJI_CATEGORIES).flat().filter((e, i, arr) => arr.indexOf(e) === i)
    : EMOJI_CATEGORIES[currentEmojiCategory];

  grid.innerHTML = filtered.map(emoji =>
    `<button class="emoji-btn" data-emoji="${emoji}">${emoji}</button>`
  ).join('');

  grid.querySelectorAll('.emoji-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const pos = messageInput.selectionStart || messageInput.value.length;
      const val = messageInput.value;
      messageInput.value = val.slice(0, pos) + btn.dataset.emoji + val.slice(pos);
      messageInput.focus();
      messageInput.selectionStart = messageInput.selectionEnd = pos + btn.dataset.emoji.length;
      closeEmojiPicker();
    });
  });
}

function toggleEmojiPicker() {
  const existing = document.getElementById('emojiPicker');
  if (existing) closeEmojiPicker();
  else { emojiPickerOpen = true; createEmojiPicker(); }
}

function closeEmojiPicker() {
  const picker = document.getElementById('emojiPicker');
  if (picker) picker.remove();
  emojiPickerOpen = false;
}

if (emojiBtn) {
  emojiBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleEmojiPicker();
  });
}

document.addEventListener('click', (e) => {
  if (emojiPickerOpen && !e.target.closest('#emojiPicker') && e.target !== emojiBtn) {
    closeEmojiPicker();
  }
  if (currentReactionPicker && !e.target.closest('.reaction-picker') && !e.target.closest('.reaction-trigger')) {
    closeReactionPicker();
  }
});

// ── Reaction Picker ───────────────────────────
const QUICK_REACTIONS = ['👍','❤️','😂','😮','😢','🔥','👏','🎉'];

function showReactionPicker(triggerEl, messageId) {
  closeReactionPicker();
  const picker = document.createElement('div');
  picker.className = 'reaction-picker';
  picker.innerHTML = QUICK_REACTIONS.map(e =>
    `<span class="reaction-option" data-emoji="${e}" data-msgid="${messageId}">${e}</span>`
  ).join('');

  const rect = triggerEl.getBoundingClientRect();
  picker.style.cssText = `position:fixed;top:${rect.top - 60}px;left:${rect.left - 60}px;`;
  document.body.appendChild(picker);
  currentReactionPicker = picker;

  picker.querySelectorAll('.reaction-option').forEach(opt => {
    opt.addEventListener('click', () => {
      toggleReaction(messageId, opt.dataset.emoji);
      closeReactionPicker();
    });
  });
}

function closeReactionPicker() {
  if (currentReactionPicker) { currentReactionPicker.remove(); currentReactionPicker = null; }
}

function toggleReaction(messageId, emoji) {
  // Send via WebSocket for real-time update
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: 'emoji_reaction',
      message_id: messageId,
      emoji: emoji,
    }));
  } else {
    // Fallback to HTTP if WebSocket not available
    fetch(REACTION_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN,
      },
      body: JSON.stringify({
        message_id: messageId,
        emoji: emoji,
      }),
    })
    .then(res => res.json())
    .then(data => {
      if (data.ok) {
        messageReactions[messageId] = data.reactions;
        renderReactions(messageId);
      }
    })
    .catch(err => {
      console.error('Failed to toggle reaction:', err);
    });
  }
}

function renderReactions(messageId) {
  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) return;
  let reactEl = msgEl.querySelector('.message-reactions');
  if (!reactEl) {
    reactEl = document.createElement('div');
    reactEl.className = 'message-reactions';
    msgEl.querySelector('.message-footer')?.before(reactEl);
  }
  const reactions = messageReactions[messageId] || {};
  reactEl.innerHTML = Object.entries(reactions).map(([emoji, users]) => {
    const mine = users.includes(CURRENT_USER);
    return `<span class="reaction-pill ${mine ? 'mine' : ''}"
                  onclick="toggleReaction('${messageId}','${emoji}')"
                  title="${users.join(', ')}">
              ${emoji} <span class="reaction-count">${users.length}</span>
            </span>`;
  }).join('');
}

// ── Edit Message ──────────────────────────────
function startEdit(messageId) {
  if (editingMessageId && editingMessageId !== messageId) cancelEdit();

  editingMessageId = messageId;
  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) return;

  const bubble = msgEl.querySelector('.message-bubble');
  const textSpan = bubble.querySelector('.msg-text');
  if (!textSpan) return;

  const originalText = textSpan.textContent;

  const editArea = document.createElement('textarea');
  editArea.className = 'msg-edit-input';
  editArea.value = originalText;
  editArea.dataset.originalText = originalText;
  editArea.rows = 1;
  textSpan.replaceWith(editArea);

  editArea.style.height = 'auto';
  editArea.style.height = Math.min(editArea.scrollHeight, 120) + 'px';
  editArea.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });

  editArea.focus();
  editArea.setSelectionRange(editArea.value.length, editArea.value.length);

  editArea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitEdit(messageId); }
    if (e.key === 'Escape') { cancelEdit(); }
  });

  if (editBar) editBar.style.display = 'block';
  sendBtn.textContent = '✓';
  sendBtn.title = 'Save edit (Enter)';
  sendBtn._editMode = true;
}

function submitEdit(messageId) {
  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) return;
  const editArea = msgEl.querySelector('.msg-edit-input');
  if (!editArea) return;
  const newContent = editArea.value.trim();
  if (!newContent) return;
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'edit_message', message_id: messageId, content: newContent }));
  }
  cancelEdit();
}

function cancelEdit() {
  if (!editingMessageId) return;
  const msgEl = document.querySelector(`[data-message-id="${editingMessageId}"]`);
  if (msgEl) {
    const editArea = msgEl.querySelector('.msg-edit-input');
    if (editArea) {
      const span = document.createElement('span');
      span.className = 'msg-text';
      span.textContent = editArea.dataset.originalText;
      editArea.replaceWith(span);
    }
  }
  editingMessageId = null;
  if (editBar) editBar.style.display = 'none';
  sendBtn.textContent = '➤';
  sendBtn.title = 'Send';
  sendBtn._editMode = false;
}

// ── Delete Message ────────────────────────────
function confirmDelete(messageId) {
  pendingDeleteId = messageId;
  document.getElementById('deleteModal').style.display = 'flex';
}

function closeDeleteModal(event) {
  if (event && event.target !== document.getElementById('deleteModal')) return;
  document.getElementById('deleteModal').style.display = 'none';
  pendingDeleteId = null;
}

function executeDelete() {
  if (!pendingDeleteId) return;
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'delete_message', message_id: pendingDeleteId }));
  }
  document.getElementById('deleteModal').style.display = 'none';
  pendingDeleteId = null;
}

// ── WebSocket ─────────────────────────────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${ROOM_SLUG}/`;

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
        replyTo:   data.reply_to  || null,
        own:       data.username === CURRENT_USER,
      });
      scrollToBottom();
      if (data.username !== CURRENT_USER) {
        playSound('receive');
        showToast(data.username, data.message.substring(0, 60));
        showBrowserNotif(data.username, data.message);
        if (document.hidden) {
          unreadCount++;
          document.title = `(${unreadCount}) ${ROOM_SLUG} — Chat`;
        }
      } else {
        playSound('send');
      }
    }
    else if (data.type === 'user_join') {
      appendSystemMessage(`${data.username} joined the room`);
    }
    else if (data.type === 'typing') {
      if (data.username !== CURRENT_USER) showTyping(data.username);
    }
    else if (data.type === 'stop_typing') {
      hideTyping();
    }
    else if (data.type === 'online_count') {
      if (onlineCountEl) onlineCountEl.textContent = data.count;
    }
    else if (data.type === 'message_read') {
      const el = document.querySelector(`[data-message-id="${data.message_id}"] .read-badge`);
      if (el) el.textContent = '✓✓';
    }
    else if (data.type === 'message_deleted') {
      handleMessageDeleted(data.message_id);
    }
    else if (data.type === 'message_edited') {
      handleMessageEdited(data.message_id, data.content);
    }
    else if (data.type === 'emoji_reaction') {
      // Update local state and render reactions
      messageReactions[data.message_id] = data.reactions;
      renderReactions(data.message_id);
    }
  };
}

function handleMessageDeleted(messageId) {
  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) return;
  msgEl.style.transition = 'opacity 0.3s, transform 0.3s';
  msgEl.style.opacity    = '0';
  msgEl.style.transform  = 'scale(0.9)';
  setTimeout(() => msgEl.remove(), 320);
}

function handleMessageEdited(messageId, newContent) {
  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) return;

  if (editingMessageId === messageId) {
    cancelEdit();
    const freshEl = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!freshEl) return;
    const textSpan = freshEl.querySelector('.msg-text');
    if (textSpan) textSpan.textContent = newContent;
    addOrUpdateEditedBadge(freshEl);
    return;
  }

  const textSpan = msgEl.querySelector('.msg-text');
  if (textSpan) {
    textSpan.textContent = newContent;
    textSpan.style.transition = 'background 0.4s';
    textSpan.style.background = 'rgba(44,165,224,0.18)';
    textSpan.style.borderRadius = '4px';
    setTimeout(() => { textSpan.style.background = ''; }, 800);
  }
  addOrUpdateEditedBadge(msgEl);
}

function addOrUpdateEditedBadge(msgEl) {
  const footer = msgEl.querySelector('.message-footer');
  if (!footer) return;
  if (!footer.querySelector('.edited-badge')) {
    const badge = document.createElement('span');
    badge.className = 'edited-badge';
    badge.textContent = 'edited';
    const timeEl = footer.querySelector('.message-time');
    if (timeEl) timeEl.after(badge);
    else footer.prepend(badge);
  }
}

function createSocket() {
  socket = new WebSocket(wsUrl);
  bindSocketEvents(socket);
}
createSocket();

// ── Typing Indicator ──────────────────────────
let typingUsers = {};

function showTyping(username) {
  typingUsers[username] = true;
  updateTypingDisplay();
}
function hideTyping(username) {
  if (username) delete typingUsers[username];
  else typingUsers = {};
  updateTypingDisplay();
}
function updateTypingDisplay() {
  const users = Object.keys(typingUsers);
  if (users.length === 0) {
    typingEl.innerHTML = '';
  } else {
    const names = users.join(', ');
    typingEl.innerHTML = `
      <div class="typing-dots"><span></span><span></span><span></span></div>
      ${escapeHtml(names)} ${users.length === 1 ? 'is typing' : 'are typing'}...
    `;
  }
}

// ── Text Message / Edit Send ──────────────────
function sendMessage() {
  if (editingMessageId && sendBtn._editMode) {
    submitEdit(editingMessageId);
    return;
  }

  const content = messageInput.value.trim();
  if (!content || !socket || socket.readyState !== WebSocket.OPEN) return;

  const payload = { message: content };
  if (replyingToId) {
    payload.reply_to_id = replyingToId;
  }

  socket.send(JSON.stringify(payload));
  messageInput.value = '';
  messageInput.style.height = 'auto';
  messageInput.focus();
  cancelReply();
}

// ── Auto-resize textarea ──────────────────────
if (messageInput) {
  messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });
}

// ── File Upload ───────────────────────────────
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
      showToast('Error', 'File size cannot exceed 10MB');
      return;
    }

    if (uploadProg) uploadProg.style.display = 'flex';
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
          type: 'file_message',
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

if (attachBtn) attachBtn.addEventListener('click', openFilePicker);

// ── Render Message ────────────────────────────
let lastAuthor = null;

function appendMessage({ content, username, timestamp, messageId, fileUrl, fileType, replyTo, own, isEdited }) {
  const isGrouped = username === lastAuthor && !replyTo;
  lastAuthor = username;

  const div = document.createElement('div');
  div.className = `message ${own ? 'own' : ''} ${isGrouped ? 'grouped' : ''}`;
  div.setAttribute('data-message-id', messageId);
  div.setAttribute('data-is-own', own ? 'true' : 'false');

  // Reply quote HTML
  let replyHtml = '';
  if (replyTo) {
    const safeUser = escapeHtml(replyTo.username);
    const safeText = escapeHtml(replyTo.text.substring(0, 80));
    replyHtml = `
      <div class="reply-quote" onclick="scrollToMessage(${replyTo.id})">
        <span class="reply-quote-author">↩ ${safeUser}</span>
        <span class="reply-quote-text">${safeText}</span>
      </div>`;
  }

  let bubbleInner = '';
  if (fileUrl) {
    if (fileType === 'image') {
      bubbleInner = `<img src="${fileUrl}" class="msg-image"
                       onclick="window.open(this.src)" alt="${escapeHtml(content)}">`;
    } else {
      bubbleInner = `<a href="${fileUrl}" class="msg-file" download>📎 ${escapeHtml(content)}</a>`;
    }
  } else {
    bubbleInner = `<span class="msg-text">${escapeHtml(content)}</span>`;
  }

  const editedBadge = isEdited ? '<span class="edited-badge">edited</span>' : '';

  // Reply button always shown; edit/delete only for own text messages
  const replyAction = `<button class="msg-action-btn reply-btn"
      onclick="startReply('${messageId}', '${escapeHtml(username)}', this)"
      title="Reply">↩</button>`;

  const ownActions = own ? `
    ${!fileUrl ? `<button class="msg-action-btn edit-btn"
        onclick="startEdit('${messageId}')" title="Edit">✏️</button>` : ''}
    <button class="msg-action-btn delete-btn"
        onclick="confirmDelete('${messageId}')" title="Delete">🗑️</button>` : '';

  div.innerHTML = `
    <div class="message-author">${escapeHtml(username)}</div>
    <div class="message-bubble">
      ${replyHtml}
      ${bubbleInner}
      <span class="reaction-trigger" title="Add reaction">😊</span>
    </div>
    <div class="message-footer">
      <span class="message-time">${timestamp}</span>
      ${editedBadge}
      ${own ? '<span class="read-badge">✓</span>' : ''}
      <span class="msg-actions">
        ${replyAction}
        ${ownActions}
      </span>
    </div>
  `;

  // Reaction trigger
  const trigger = div.querySelector('.reaction-trigger');
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    showReactionPicker(trigger, messageId);
  });

  chatMessages.appendChild(div);

  if (!own && socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'mark_as_read', message_id: messageId }));
  }
}

function appendSystemMessage(text) {
  lastAuthor = null;
  const div = document.createElement('div');
  div.className = 'message system';
  div.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function scrollToBottom(smooth = false) {
  chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Toast ─────────────────────────────────────
function showToast(title, body) {
  if (!toastContainer) return;
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerHTML = `<div class="toast-title">💬 ${escapeHtml(String(title))}</div>
                 <div class="toast-body">${escapeHtml(String(body).substring(0,80))}</div>`;
  toastContainer.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; }, 3500);
  setTimeout(() => t.remove(), 3800);
}

// ── Browser Notification ──────────────────────
let notifBtn = document.getElementById('notifBtn');
function showBrowserNotif(username, message) {
  if (!document.hidden || !('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;
  try {
    const n = new Notification(`💬 ${username}`, { body: message, icon: '/static/favicon.ico' });
    n.onclick = () => { window.focus(); n.close(); };
  } catch (e) { /* ignore */ }
}
if (notifBtn) {
  if (Notification.permission === 'granted') {
    notifBtn.textContent = '🔔';
    notifBtn.style.color = 'var(--green)';
    notifBtn.title = 'Notifications Enabled';
  }
  notifBtn.addEventListener('click', async () => {
    if (!('Notification' in window)) { showToast('Info', 'Notifications not supported in this browser'); return; }
    const perm = await Notification.requestPermission();
    if (perm === 'granted') {
      notifBtn.style.color = 'var(--green)';
      showToast('Notification', '🔔 Notifications enabled ✓');
    }
  });
}

// ── Typing Events ─────────────────────────────
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

// ── Events ────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    unreadCount = 0;
    document.title = `${ROOM_SLUG} — Django Chat`;
  }
});

scrollToBottom();