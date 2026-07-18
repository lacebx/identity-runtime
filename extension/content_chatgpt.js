/**
 * content_chatgpt.js
 * Content script injected into chat.openai.com
 * Intercepts prompts and responses to inject/extract identity context.
 */

(function () {
  'use strict';

  const RUNTIME_API = 'http://localhost:8765';
  let currentIdentityId = null;
  let identityContext = null;

  // ─── Bootstrap ───────────────────────────────────────────────────────────────

  async function init() {
    const config = await getConfig();
    currentIdentityId = config.activeIdentityId || null;
    if (currentIdentityId) {
      identityContext = await fetchIdentityContext(currentIdentityId);
      console.log('[IdentityRuntime] Loaded identity:', currentIdentityId);
    }
    observePromptSubmit();
    observeResponseStream();
  }

  // ─── Config Helpers ──────────────────────────────────────────────────────────

  function getConfig() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'GET_CONFIG' }, (resp) => {
        resolve(resp || {});
      });
    });
  }

  async function fetchIdentityContext(identityId) {
    try {
      const res = await fetch(`${RUNTIME_API}/context/${identityId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recent_messages: [], max_tokens: 800 }),
      });
      const data = await res.json();
      return data.context_block || null;
    } catch (e) {
      console.warn('[IdentityRuntime] Could not fetch identity context:', e);
      return null;
    }
  }

  // ─── Prompt Interception ─────────────────────────────────────────────────────

  function observePromptSubmit() {
    // ChatGPT uses a textarea with data-id="prompt-textarea"
    const observer = new MutationObserver(() => {
      const textarea = document.querySelector('#prompt-textarea');
      if (textarea && !textarea.dataset.irPatched) {
        textarea.dataset.irPatched = 'true';
        patchTextarea(textarea);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function patchTextarea(textarea) {
    const form = textarea.closest('form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      if (!identityContext) return;
      // Prepend identity context as a hidden system note before submission
      // We inject it by temporarily prepending to the textarea value
      const original = textarea.value;
      if (!original.includes('[IdentityContext]')) {
        const augmented = `[IdentityContext]\n${identityContext}\n[/IdentityContext]\n\n${original}`;
        // Use React's synthetic event trick to update the controlled input
        const nativeInputSetter = Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype,
          'value'
        ).set;
        nativeInputSetter.call(textarea, augmented);
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }, { capture: true });
  }

  // ─── Response Observation ────────────────────────────────────────────────────

  function observeResponseStream() {
    // Watch for completed assistant messages and store them as memories
    const observer = new MutationObserver(async (mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          // ChatGPT marks complete turns with data-message-author-role="assistant"
          const assistantMsg = node.querySelector
            ? node.querySelector('[data-message-author-role="assistant"]')
            : null;
          if (assistantMsg) {
            const text = assistantMsg.innerText?.trim();
            if (text && currentIdentityId) {
              await storeMemory(currentIdentityId, text);
            }
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  async function storeMemory(identityId, content) {
    try {
      await fetch(`${RUNTIME_API}/memory/${identityId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content,
          source: 'chatgpt',
          type: 'episodic',
        }),
      });
    } catch (e) {
      console.warn('[IdentityRuntime] Memory store failed:', e);
    }
  }

  // ─── Identity Switcher UI ────────────────────────────────────────────────────

  function injectIdentityBadge() {
    if (document.getElementById('ir-identity-badge')) return;
    const badge = document.createElement('div');
    badge.id = 'ir-identity-badge';
    badge.style.cssText = `
      position: fixed;
      bottom: 80px;
      right: 16px;
      background: #1a1a2e;
      color: #e0e0ff;
      border: 1px solid #4444aa;
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 12px;
      font-family: monospace;
      z-index: 9999;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    `;
    badge.title = 'Identity Runtime — click to switch identity';
    updateBadgeText(badge);
    badge.addEventListener('click', () => {
      chrome.runtime.sendMessage({ type: 'OPEN_POPUP' });
    });
    document.body.appendChild(badge);
  }

  function updateBadgeText(badge) {
    badge.textContent = currentIdentityId
      ? `⬡ ${currentIdentityId}`
      : '⬡ No Identity';
  }

  // ─── Message Listener ────────────────────────────────────────────────────────

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'IDENTITY_CHANGED') {
      currentIdentityId = message.identityId;
      fetchIdentityContext(currentIdentityId).then((ctx) => {
        identityContext = ctx;
        const badge = document.getElementById('ir-identity-badge');
        if (badge) updateBadgeText(badge);
      });
    }
  });

  // ─── Start ───────────────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      init();
      injectIdentityBadge();
    });
  } else {
    init();
    injectIdentityBadge();
  }
})();
