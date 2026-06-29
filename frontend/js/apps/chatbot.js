const API = '/api/chat';

const modelSelect   = document.getElementById('modelSelect');
const tempSlider    = document.getElementById('tempSlider');
const tempVal       = document.getElementById('tempVal');
const systemPrompt  = document.getElementById('systemPrompt');
const clearBtn      = document.getElementById('clearBtn');
const chatMessages  = document.getElementById('chatMessages');
const chatForm      = document.getElementById('chatForm');
const chatInput     = document.getElementById('chatInput');
const sendBtn       = document.getElementById('sendBtn');

let conversationHistory = [];

// ---- Initialise ----------------------------------------------------------

tempSlider.addEventListener('input', () => { tempVal.textContent = tempSlider.value; });

clearBtn.addEventListener('click', () => {
  conversationHistory = [];
  chatMessages.innerHTML = '';
});

// Load available models
(async () => {
  try {
    const data = await (await fetch(`${API}/models`)).json();
    const models = data.models || [];
    modelSelect.innerHTML = models.length
      ? models.map((m) => `<option value="${escapeAttr(m.name)}">${escapeHtml(m.name)}</option>`).join('')
      : '<option value="">No models found</option>';
  } catch {
    modelSelect.innerHTML = '<option value="">Ollama unavailable</option>';
  }
})();

// ---- Send message --------------------------------------------------------

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const content = chatInput.value.trim();
  if (!content) return;
  chatInput.value = '';

  appendMessage('user', content);
  conversationHistory.push({ role: 'user', content });

  sendBtn.disabled = true;
  const assistantEl = appendMessage('assistant', '');

  const system = systemPrompt.value.trim();
  const payload = {
    model:       modelSelect.value,
    messages:    conversationHistory,
    stream:      true,
    temperature: parseFloat(tempSlider.value),
    system:      system || null,
  };

  try {
    const resp = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;
      assistantEl.innerHTML = renderMarkdown(fullText);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    conversationHistory.push({ role: 'assistant', content: fullText });
  } catch (err) {
    assistantEl.innerHTML = `<span style="color:#f87">Error: ${escapeHtml(err.message)}</span>`;
  } finally {
    sendBtn.disabled = false;
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});

// Ctrl+Enter to send
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) chatForm.requestSubmit();
});

// ---- Helpers -------------------------------------------------------------

function appendMessage(role, content) {
  const el = document.createElement('div');
  el.className = `chat-bubble chat-bubble--${role}`;
  el.innerHTML = renderMarkdown(content);
  chatMessages.appendChild(el);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return el;
}

function renderMarkdown(text) {
  if (window.marked) return marked.parse(text);
  return escapeHtml(text).replace(/\n/g, '<br>');
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escapeAttr(s) {
  return String(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
