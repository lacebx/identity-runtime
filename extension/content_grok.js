/**
 * content_grok.js
 * Content script injected into grok.com (xAI Grok)
 * Mirrors the ChatGPT bridge but adapted for Grok's DOM structure.
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
      console.log('[IdentityRuntime:Grok] Loaded identity:', currentIdentityId);
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
      console.warn('[IdentityRuntime:Grok] Could not fetch identity context:', e);
      return null;
    }
  }

  // ─── Prompt Interception ─────────────────────────────────────────────────────

  function observePromptSubmit() {
    // Grok uses a contenteditable div for its prompt input
    const observer = new MutationObserver(() => {
      // Grok's input: a div with role="textbox" or a textarea in the composer
      const input =
        document.querySelector('[data-testid="grok-compose-input"]') ||
        document.querySelector('div[contenteditable="true"][role="textbox"]');
      if (input && !input.dataset.irPatched) {
        input.dataset.irPatched = 'true';
        patchInput(input);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function patchInput(input) {
    // Listen for Enter key (submit) on the contenteditable
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && identityContext) {
        const currentText = input.innerText || '';
        if (!currentText.includes('[IdentityContext]')) {
          const prefix = `[IdentityContext]\n${identityContext}\n[/IdentityContext]\n\n`;
          // For contenteditable, insert at the beginning
          const selection = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(input);
          range.collapse(true); // move to start
          selection.removeAllRanges();
          selection.addRange(range);
          document.execCommand('insertText', false, prefix);
        }
      }
    }, { capture: true });
  }

  // ─── Response Observation ────────────────────────────────────────────────────

  function observeResponseStream() {
    const observer = new MutationObserver(async (mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          // Grok labels assistant messages with data-message-author="assistant"
          // or a class-based selector — use a broad query
          const assistantMsg =
            node.querySelector
              ? node.querySelector('[data-message-author="assistant"], .assistant-message')
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
          source: 'grok',
          type: 'episodic',
        }),
      });
    } catch (e) {
      console.warn('[IdentityRuntime:Grok] Memory store failed:', e);
    }
  }

  // ─── Identity Badge UI ───────────────────────────────────────────────────────

  function injectIdentityBadge() {
    if (document.getElementById('ir-identity-badge')) return;
    const badge = document.createElement('div');
    badge.id = 'ir-identity-badge';
    badge.style.cssText = `
      position: fixed;
      bottom: 80px;
      right: 16px;
      background: #0d0d1a;
      color: #c8b8ff;
      border: 1px solid #6644cc;
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 12px;
      font-family: monospace;
      z-index: 9999;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.5);
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
