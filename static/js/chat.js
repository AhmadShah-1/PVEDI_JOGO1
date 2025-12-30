// Chat Module
// Handles user input, streaming responses, and chat UI updates

const ChatModule = (() => {
  const dom = {
    chatContainer: document.getElementById('chat-container'),
    questionInput: document.getElementById('question'),
    askBtn: document.getElementById('ask-btn'),
    clearChatBtn: document.getElementById('clear-chat')
  };

  let currentController = null;

  function init() {
    dom.askBtn.addEventListener('click', handleAsk);
    dom.clearChatBtn.addEventListener('click', clearChat);
    dom.questionInput.addEventListener('input', checkInput);
    
    // Listen for changes on doc_id (might be created dynamically)
    document.addEventListener('change', (e) => {
      if (e.target && e.target.id === 'doc_id') {
        checkInput();
      }
    });

    // Initial check
    checkInput();
  }

  function checkInput() {
    // Get doc_id dynamically in case it's created after page load
    const docSelect = document.getElementById('doc_id');
    
    // Requires document to be selected
    if (docSelect && docSelect.value && dom.questionInput.value.trim()) {
      dom.askBtn.disabled = false;
    } else {
      dom.askBtn.disabled = true;
    }
  }

  function clearChat() {
    dom.chatContainer.innerHTML = '<div style="color: #999; text-align: center; margin-top: 50px;">Start a new conversation...</div>';
  }

  function appendMessage(role, text) {
    if (dom.chatContainer.querySelector('div[style*="text-align: center"]')) {
      dom.chatContainer.innerHTML = '';
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    if (role === 'user') {
      msgDiv.textContent = text;
    } else {
      const contentDiv = document.createElement('span');
      contentDiv.className = 'text-content';
      // Do not set textContent immediately if it's meant to be streamed
      contentDiv.textContent = text;
      msgDiv.appendChild(contentDiv);
    }

    dom.chatContainer.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
  }

  function scrollToBottom() {
    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
  }

  async function handleAsk() {
    const docSelect = document.getElementById('doc_id');
    const docId = docSelect ? docSelect.value : null;
    const question = dom.questionInput.value.trim();
    if (!docId || !question) return;

    if (currentController) currentController.abort();
    currentController = new AbortController();

    dom.askBtn.disabled = true;
    appendMessage('user', question);
    const assistantBubble = appendMessage('assistant', '');
    const assistantText = assistantBubble.querySelector('.text-content');
    assistantText.classList.add('loading-cursor');

    dom.questionInput.value = '';

    // Clear previous chat content if it was the placeholder
    if (dom.chatContainer.querySelector('div[style*="text-align: center"]')) {
      dom.chatContainer.innerHTML = '';
    }

    try {
      const response = await fetch('/ask_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId, question: question }),
        signal: currentController.signal
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); 

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            if (data.type === 'meta') {
              // Dispatch event for other modules
              const event = new CustomEvent('rag-meta', { detail: data });
              window.dispatchEvent(event);

              // Update Chat Metadata
              const pagesInfo = data.pages.length > 0 
                ? `Answer found on pages: ${data.pages.join(', ')}` 
                : 'No specific pages referenced.';
              
              const metaDiv = document.createElement('div');
              metaDiv.className = 'meta-info';
              metaDiv.textContent = pagesInfo;
              assistantBubble.appendChild(metaDiv);
              
            } else if (data.type === 'token') {
              assistantText.textContent += data.content;
              scrollToBottom();
            }
          } catch (e) {
            console.warn('Error parsing JSON line:', e);
          }
        }
      }

    } catch (err) {
      if (err.name !== 'AbortError') {
        assistantText.textContent += "\n[Error: " + err.message + "]";
      }
    } finally {
      assistantText.classList.remove('loading-cursor');
      dom.askBtn.disabled = false;
      checkInput(); 
      currentController = null;
    }
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', ChatModule.init);

