import { useEffect, useRef, useState } from "react";

export default function Composer({ busy, statusLine, onSend, onStop }) {
  const [text, setText] = useState("");
  const taRef = useRef(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [text]);

  useEffect(() => {
    if (!busy && taRef.current) taRef.current.focus();
  }, [busy]);

  const submit = () => {
    if (busy) return;
    if (!text.trim()) return;
    onSend(text.trim());
    setText("");
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

  return (
    <footer className="composer-area">
      <div className="composer-inner">
        <div className="composer">
          <textarea
            ref={taRef}
            id="input"
            rows="1"
            placeholder="Message a locally installed model…  (Enter to send)"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button id="sendBtn" title="Send" aria-label="Send" disabled={busy} onClick={submit}>
            &#8599;
          </button>
          <button id="stopBtn" className="btn" disabled={!busy} onClick={onStop}>
            Stop
          </button>
        </div>
        <div className="statusline" aria-live="polite">
          {statusLine.map((p, i) => (
            <span key={i} style={p.color ? { color: p.color } : undefined}>
              {p.text}
            </span>
          ))}
        </div>
      </div>
    </footer>
  );
}