/**
 * Saffron Grand — Embeddable Concierge Chat Widget
 * ---------------------------------------------------
 * Drop this one file into any website via:
 *   <script src="widget.js"></script>
 * placed just before the closing </body> tag.
 *
 * It injects a floating chat bubble (bottom-right), and talks to
 * your FastAPI backend's /chat endpoint. No other dependencies.
 *
 * CONFIGURE these four values before handing this to a client:
 */
const SAFFRON_CONFIG = {
  API_URL: "https://saffron-grand-indore.onrender.com/chat", // your Render backend
  API_KEY: "saffron-grand-384hgw",            // set this to your CHATBOT_API_KEY value, or leave "" if you didn't set one
  HOTEL_NAME: "The Saffron Grand",
  ACCENT_COLOR: "#b8863f", // a warm gold, matches a hotel brand feel — change per client
};

(function () {
  "use strict";

  const cfg = SAFFRON_CONFIG;
  let history = []; // [{role: "user"|"assistant", content: "..."}]
  let isOpen = false;
  let isSending = false;

  // ---------- Styles ----------
  const style = document.createElement("style");
  style.textContent = `
    #sg-chat-bubble {
      position: fixed; bottom: 24px; right: 24px;
      width: 60px; height: 60px; border-radius: 50%;
      background: ${cfg.ACCENT_COLOR}; color: white;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.25);
      z-index: 99998; transition: transform 0.15s ease;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #sg-chat-bubble:hover { transform: scale(1.06); }
    #sg-chat-bubble svg { width: 28px; height: 28px; fill: white; }

    #sg-chat-window {
      position: fixed; bottom: 96px; right: 24px;
      width: 360px; max-width: 92vw; height: 520px; max-height: 75vh;
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.25);
      display: none; flex-direction: column; overflow: hidden;
      z-index: 99999; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #sg-chat-window.open { display: flex; }

    #sg-chat-header {
      background: ${cfg.ACCENT_COLOR}; color: white;
      padding: 14px 16px; font-weight: 600; font-size: 15px;
      display: flex; justify-content: space-between; align-items: center;
    }
    #sg-chat-close { cursor: pointer; font-size: 18px; opacity: 0.85; }
    #sg-chat-close:hover { opacity: 1; }

    #sg-chat-messages {
      flex: 1; overflow-y: auto; padding: 14px;
      background: #faf8f5; display: flex; flex-direction: column; gap: 10px;
    }
    .sg-msg { max-width: 85%; padding: 9px 13px; border-radius: 12px;
      font-size: 13.5px; line-height: 1.45; white-space: pre-wrap; word-wrap: break-word; }
    .sg-msg.user { align-self: flex-end; background: ${cfg.ACCENT_COLOR}; color: white; border-bottom-right-radius: 3px; }
    .sg-msg.assistant { align-self: flex-start; background: #eee; color: #222; border-bottom-left-radius: 3px; }
    .sg-msg.typing { align-self: flex-start; background: #eee; color: #888; font-style: italic; }

    #sg-chat-inputRow {
      display: flex; border-top: 1px solid #eee; padding: 10px; gap: 8px;
    }
    #sg-chat-input {
      flex: 1; border: 1px solid #ddd; border-radius: 20px;
      padding: 9px 14px; font-size: 13.5px; outline: none;
    }
    #sg-chat-input:focus { border-color: ${cfg.ACCENT_COLOR}; }
    #sg-chat-send {
      background: ${cfg.ACCENT_COLOR}; color: white; border: none;
      border-radius: 20px; padding: 0 16px; font-size: 13.5px; font-weight: 600;
      cursor: pointer;
    }
    #sg-chat-send:disabled { opacity: 0.5; cursor: default; }
  `;
  document.head.appendChild(style);

  // ---------- DOM ----------
  const bubble = document.createElement("div");
  bubble.id = "sg-chat-bubble";
  bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/></svg>`;

  const win = document.createElement("div");
  win.id = "sg-chat-window";
  win.innerHTML = `
    <div id="sg-chat-header">
      <span>${cfg.HOTEL_NAME} Concierge</span>
      <span id="sg-chat-close">✕</span>
    </div>
    <div id="sg-chat-messages"></div>
    <div id="sg-chat-inputRow">
      <input id="sg-chat-input" type="text" placeholder="Ask about rooms, dining, spa..." />
      <button id="sg-chat-send">Send</button>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(win);

  const messagesEl = win.querySelector("#sg-chat-messages");
  const inputEl = win.querySelector("#sg-chat-input");
  const sendBtn = win.querySelector("#sg-chat-send");
  const closeBtn = win.querySelector("#sg-chat-close");

  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = "sg-msg " + role;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function greetIfEmpty() {
    if (messagesEl.children.length === 0) {
      addMessage("assistant", `Welcome to ${cfg.HOTEL_NAME}! Ask me about rooms, dining, spa, or anything else about your stay.`);
    }
  }

  bubble.addEventListener("click", () => {
    isOpen = !isOpen;
    win.classList.toggle("open", isOpen);
    if (isOpen) {
      greetIfEmpty();
      inputEl.focus();
    }
  });
  closeBtn.addEventListener("click", () => {
    isOpen = false;
    win.classList.remove("open");
  });

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || isSending) return;

    addMessage("user", text);
    inputEl.value = "";
    isSending = true;
    sendBtn.disabled = true;

    const typingEl = addMessage("typing", "Typing...");
    typingEl.classList.add("typing");

    try {
      const headers = { "Content-Type": "application/json" };
      if (cfg.API_KEY) headers["x-api-key"] = cfg.API_KEY;

      const res = await fetch(cfg.API_URL, {
        method: "POST",
        headers,
        body: JSON.stringify({ question: text, history }),
      });

      typingEl.remove();

      if (!res.ok) {
        addMessage("assistant", "Sorry, something went wrong on our end. Please try again in a moment.");
        isSending = false;
        sendBtn.disabled = false;
        return;
      }

      const data = await res.json();
      addMessage("assistant", data.answer);

      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: data.answer });

      // Keep history from growing unbounded in the browser tab
      if (history.length > 20) history = history.slice(-20);
    } catch (err) {
      typingEl.remove();
      addMessage("assistant", "I'm having trouble connecting right now. Please try again shortly.");
    }

    isSending = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();
