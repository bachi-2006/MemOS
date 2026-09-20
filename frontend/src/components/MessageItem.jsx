import { useState } from "react";
import { renderMarkdown } from "../lib/markdown.js";
import { fmtMeta, fmtTime } from "../lib/util.js";

function MiniButton({ label, icon, onClick, disabled, title, active }) {
  return (
    <button
      className={"msg-action-btn" + (active ? " active" : "")}
      disabled={disabled}
      title={title || label}
      onClick={onClick}
    >
      {icon && <span className="btn-icon">{icon}</span>}
      <span>{label}</span>
    </button>
  );
}

export default function MessageItem({
  m,
  streamingBusy,
  onRegenerate,
  onSaveAsMemory,
  onToast,
}) {
  const [openReasoning, setOpenReasoning] = useState(false);
  const [openRecalled, setOpenRecalled] = useState(false);
  const [copied, setCopied] = useState(false);
  const isStreaming = !!m.streaming;

  const handleCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(m.content || "");
      setCopied(true);
      if (onToast) onToast("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSaveMemory = () => {
    if (onSaveAsMemory) {
      onSaveAsMemory(m.content);
    }
  };

  // Safe time string
  const timeStr = fmtTime(m.ts);

  // User Message
  if (m.role === "user") {
    const userText = typeof m.content === "string" ? m.content : (m.content != null ? String(m.content) : "");
    const safeRecalled = Array.isArray(m.recalledMemories) ? m.recalledMemories : [];

    return (
      <div className="msg user">
        <div className="msg-header">
          <div className="avatar user-avatar">You</div>
          {timeStr && <span className="msg-time">{timeStr}</span>}
        </div>

        <div className="body">
          {/* Recalled Memories Pill (if this prompt triggered memories) */}
          {safeRecalled.length > 0 && (
            <div className="recalled-banner">
              <button
                className="recalled-toggle"
                onClick={() => setOpenRecalled(!openRecalled)}
                title="Click to view memories injected into this prompt context"
              >
                <span className="recalled-icon">🧠</span>
                <span>{safeRecalled.length} Context Memories Recalled</span>
                <span className="recalled-arrow">{openRecalled ? "▲" : "▼"}</span>
              </button>
              {openRecalled && (
                <div className="recalled-list">
                  {safeRecalled.map((rm, idx) => {
                    const rmText = typeof rm === "string"
                      ? rm
                      : (rm?.content || rm?.text || rm?.fact || (typeof rm === "object" ? JSON.stringify(rm) : String(rm)));
                    const rmScore = rm && typeof rm === "object" && typeof (rm.score ?? rm.relevance_score) === "number" ? (rm.score ?? rm.relevance_score) : null;
                    return (
                      <div key={idx} className="recalled-item">
                        <span className="recalled-bullet">•</span>
                        <span className="recalled-text">{rmText}</span>
                        {rmScore != null && (
                          <span className="recalled-score">{(rmScore * 100).toFixed(0)}% match</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <div className="bubble user-bubble">{userText}</div>

          <div className="msg-actions">
            <MiniButton
              icon={copied ? "✓" : "📋"}
              label={copied ? "Copied" : "Copy"}
              onClick={handleCopy}
            />
            {onSaveAsMemory && (
              <MiniButton
                icon="🧠"
                label="Save as Memory"
                title="Save this message to Long-Term Memory Bank"
                onClick={handleSaveMemory}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  const modelLabel = typeof m.meta === "string"
    ? m.meta.replace(/ · error$/, "")
    : (m.meta ? String(m.meta) : "assistant");

  const reasoningText = typeof m.reasoning === "string"
    ? m.reasoning
    : (m.reasoning ? String(m.reasoning) : "");
  const reasoningWords = reasoningText.trim() ? reasoningText.trim().split(/\s+/).length : 0;

  const assistantContent = typeof m.content === "string"
    ? m.content
    : (m.content != null ? String(m.content) : "");

  const safeExtracted = Array.isArray(m.extractedMemories) ? m.extractedMemories : [];

  return (
    <div className={"msg assistant" + (isStreaming ? " streaming" : "")}>
      <div className="msg-header">
        <div className="avatar assistant-avatar">
          <span className="bot-icon">🤖</span>
          <span className="model-name">{modelLabel}</span>
        </div>
        <div className="msg-header-right">
          {isStreaming && <span className="streaming-badge animate-pulse">Generating…</span>}
          {timeStr && <span className="msg-time">{timeStr}</span>}
        </div>
      </div>

      <div className="body">
        {/* Deep Reasoning Accordion (<think> blocks) */}
        {reasoningText ? (
          <div className={"reasoning-container" + (isStreaming || openReasoning ? " open" : "")}>
            <button
              className="reasoning-toggle-btn"
              aria-expanded={isStreaming || openReasoning ? "true" : "false"}
              onClick={() => setOpenReasoning(!openReasoning)}
            >
              <span className="thinking-sparkle">✨</span>
              <span className="thinking-title">
                {isStreaming ? "Reasoning process…" : `Thought process (${reasoningWords} words)`}
              </span>
              <span className="reasoning-arrow">{isStreaming || openReasoning ? "▲" : "▼"}</span>
            </button>
            <div className="reasoning-content">{reasoningText}</div>
          </div>
        ) : null}

        {/* Message Content with Markdown & Cursor */}
        <div
          className="bubble assistant-bubble markdown-body"
          dangerouslySetInnerHTML={{
            __html: renderMarkdown(assistantContent) + (isStreaming ? '<span class="typing-cursor"></span>' : ""),
          }}
        />

        {/* Live Extracted Memories Badge (if background analysis learned facts) */}
        {safeExtracted.length > 0 && (
          <div className="extracted-banner">
            <span className="extracted-sparkle">✨</span>
            <span className="extracted-label">New knowledge learned from this turn:</span>
            <div className="extracted-chips">
              {safeExtracted.map((em, idx) => {
                const emText = typeof em === "string"
                  ? em
                  : (em?.content || em?.fact || em?.text || em?.name || (typeof em === "object" ? JSON.stringify(em) : String(em)));
                return (
                  <span key={idx} className="extracted-chip">
                    {emText}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Actions Toolbar */}
        <div className="msg-actions">
          <MiniButton
            icon={copied ? "✓" : "📋"}
            label={copied ? "Copied" : "Copy"}
            onClick={handleCopy}
          />
          <MiniButton
            icon="🔄"
            label="Regenerate"
            disabled={streamingBusy}
            onClick={onRegenerate}
            title="Regenerate this response"
          />
          {onSaveAsMemory && (
            <MiniButton
              icon="🧠"
              label="Save Fact"
              title="Save key takeaways to Long-Term Memory"
              onClick={handleSaveMemory}
            />
          )}
          {!isStreaming && m.meta ? (
            <span className="meta-tag">{fmtMeta(m)}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}