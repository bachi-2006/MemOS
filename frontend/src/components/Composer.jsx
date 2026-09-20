import { useEffect, useRef, useState } from "react";
import { estTokens } from "../lib/util.js";

const QUICK_STARTERS = [
  { text: "What do you know about me and my projects?", icon: "🧠" },
  { text: "Help me design a clean full-stack architecture for my application.", icon: "⚡" },
  { text: "Extract and summarize all the technical decisions we've discussed so far.", icon: "📝" },
  { text: "What are the key differences between SQLite and PostgreSQL in MemOS?", icon: "💡" },
];

export default function Composer({
  busy = false,
  statusLine = [],
  onSend,
  onStop,
  activeModel = "",
  recallOn = false,
  onToggleRecall,
  hasMessages = false,
}) {
  const [text, setText] = useState("");
  const taRef = useRef(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "44px";
    const nextH = Math.max(44, Math.min(ta.scrollHeight || 44, 220));
    ta.style.height = nextH + "px";
  }, [text]);

  useEffect(() => {
    if (!busy && taRef.current) taRef.current.focus();
  }, [busy]);

  const submit = () => {
    if (busy) return;
    if (!text.trim()) return;
    onSend(text.trim());
    setText("");
    if (taRef.current) taRef.current.style.height = "44px";
  };

  const handleStarterClick = (starterText) => {
    if (busy) return;
    onSend(starterText);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!busy) submit();
    } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (!busy) submit();
    } else if (e.key === "Escape" && busy) {
      e.preventDefault();
      onStop();
    }
  };

  const tokenEstimate = estTokens(text);

  return (
    <footer className="composer-area">
      <div className="composer-inner">
        {/* Quick starter chips for new conversation */}
        {!hasMessages && (
          <div className="quick-starters">
            <span className="starter-label">Try asking:</span>
            {QUICK_STARTERS.map((s, idx) => (
              <button
                key={idx}
                className="starter-chip"
                onClick={() => handleStarterClick(s.text)}
                disabled={busy}
              >
                <span className="starter-icon">{s.icon}</span>
                <span>{s.text}</span>
              </button>
            ))}
          </div>
        )}

        {/* Composer Card */}
        <div className="composer-card">
          <div className="composer-toolbar-top">
            <div className="toolbar-left">
              {activeModel && (
                <span className="active-model-chip" title="Active Ollama model">
                  <span className="chip-dot">●</span>
                  <span>{activeModel}</span>
                </span>
              )}
              {onToggleRecall && (
                <button
                  className={"recall-toggle-chip" + (recallOn ? " on" : "")}
                  onClick={onToggleRecall}
                  title="Toggle personalized long-term memory retrieval"
                >
                  <span className="chip-icon">{recallOn ? "✨" : "⚡"}</span>
                  <span>{recallOn ? "Personalized Memory: Active" : "Raw Zero-Shot Mode"}</span>
                </button>
              )}
            </div>

            <div className="toolbar-right">
              {text.trim() && (
                <span className="token-counter" title="Estimated prompt tokens">
                  ~{tokenEstimate} tokens
                </span>
              )}
            </div>
          </div>

          <div className="composer-input-row">
            <textarea
              ref={taRef}
              id="composerTextarea"
              rows="1"
              style={{ minHeight: "44px" }}
              placeholder="Send a message to MemOS... (Enter to send, Shift+Enter for newline)"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKeyDown}
            />

            <div className="composer-buttons">
              {busy ? (
                <button
                  id="stopBtn"
                  className="btn-stop-generating animate-pulse"
                  title="Stop generating response (Esc)"
                  onClick={onStop}
                >
                  <span className="stop-icon">■</span>
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  id="sendBtn"
                  className={"btn-send" + (text.trim() ? " active" : "")}
                  title="Send message (Enter)"
                  aria-label="Send"
                  disabled={!text.trim()}
                  onClick={submit}
                >
                  <span className="send-arrow">➔</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Real-time status feedback line */}
        <div className="statusline" aria-live="polite">
          {(Array.isArray(statusLine) ? statusLine : []).map((p) => (
            <span key={p.id || p.text} className="status-badge" style={p.color ? { color: p.color, borderColor: p.color } : undefined}>
              {p.text}
            </span>
          ))}
        </div>
      </div>
    </footer>
  );
}