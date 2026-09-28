import { useEffect, useRef, useState, useMemo } from "react";
import MessageItem from "./MessageItem.jsx";
import Composer from "./Composer.jsx";

function formatRelativeTime(ts) {
  if (!ts) return "Recently";
  const ms = typeof ts === "string" ? new Date(ts).getTime() : ts;
  if (isNaN(ms)) return "Recently";
  const diffSec = Math.floor((Date.now() - ms) / 1000);
  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function ChatView({
  session,
  busy,
  statusLine,
  onSend,
  onStop,
  onRegenerate,
  activeModel,
  recallOn,
  onToggleRecall,
  memItems = [],
  onMemAdd,
  onMemPin,
  onMemDelete,
  onMemToggleMute,
  onToast,
}) {
  const scrollRef = useRef(null);
  const stickRef = useRef(true);
  const [showMemoryDrawer, setShowMemoryDrawer] = useState(false);
  const [memSearchQuery, setMemSearchQuery] = useState("");
  const [quickFact, setQuickFact] = useState("");

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 90;
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [session?.messages]);

  const handleSaveAsMemory = async (content) => {
    if (!content || !content.trim()) return;
    if (onMemAdd) {
      await onMemAdd(content.trim(), { tags: ["saved_from_chat"] });
      if (onToast) onToast("✨ Saved message to Long-Term Memory!");
    }
  };

  const handleAddQuickFact = async () => {
    if (!quickFact.trim()) return;
    if (onMemAdd) {
      await onMemAdd(quickFact.trim(), { tags: ["user_fact"] });
      setQuickFact("");
      if (onToast) onToast("✨ New fact recorded in Long-Term Memory!");
    }
  };

  const filteredMemories = memItems.filter((m) => {
    if (!memSearchQuery) return true;
    const match = (m.content + " " + (m.tags || []).join(" ")).toLowerCase();
    return match.includes(memSearchQuery.toLowerCase());
  });

  const activeRecalledMap = useMemo(() => {
    const map = new Map();
    (session?.messages || []).forEach((msg) => {
      if (Array.isArray(msg.recalledMemories)) {
        msg.recalledMemories.forEach((rm) => {
          if (rm.id) map.set(rm.id, rm);
          if (rm.content) map.set(rm.content.toLowerCase().trim(), rm);
        });
      }
    });
    return map;
  }, [session?.messages]);

  const hasMessages = Boolean(session && session.messages && session.messages.length > 0);

  return (
    <div className="chat-layout-wrapper">
      <div className={"chat-main-column" + (showMemoryDrawer ? " with-drawer" : "")}>
        {/* Chat Subheader Bar */}
        <div className="chat-subheader">
          <div className="subheader-left">
            <span className="session-title-pill">
              {session?.title || "New Conversation"}
            </span>
            <span className="message-counter">
              {session?.messages?.length || 0} messages
            </span>
          </div>

          <div className="subheader-right">
            <button
              className={"btn-drawer-toggle" + (showMemoryDrawer ? " active" : "")}
              onClick={() => setShowMemoryDrawer(!showMemoryDrawer)}
              title="Toggle In-Chat Memory & Context Inspector Drawer"
            >
              <span className="icon">🧠</span>
              <span>Memory Drawer ({memItems.length})</span>
              <span className="badge-arrow">{showMemoryDrawer ? "→" : "←"}</span>
            </button>
          </div>
        </div>

        {/* Messages Stream */}
        <div className="messages" id="messages" ref={scrollRef} onScroll={onScroll}>
          {hasMessages ? (
            <div className="messages-inner">
              {(session?.messages || []).map((m) => (
                <MessageItem
                  key={m.id}
                  m={m}
                  streamingBusy={busy}
                  onRegenerate={onRegenerate}
                  onSaveAsMemory={handleSaveAsMemory}
                  onToast={onToast}
                />
              ))}
            </div>
          ) : (
            <div className="empty-chat-hero">
              <div className="hero-icon-ring">
                <span className="hero-icon">🧠</span>
              </div>
              <h2 className="hero-title">Welcome to MemOS</h2>
              <p className="hero-desc">
                An adaptive, persistent memory companion for local LLMs.
                MemOS recalls relevant facts across conversations, manages importance decay,
                and extracts structured knowledge automatically.
              </p>

              <div className="hero-features-grid">
                <div className="feature-card">
                  <span className="feature-icon">✨</span>
                  <div className="feature-title">Personalized Recall</div>
                  <div className="feature-sub">Semantic vector similarity injects relevant context into prompts.</div>
                </div>
                <div className="feature-card">
                  <span className="feature-icon">🧹</span>
                  <div className="feature-title">Adaptive Decay</div>
                  <div className="feature-sub">Ebbinghaus forgetting curves keep your memory store compact.</div>
                </div>
                <div className="feature-card">
                  <span className="feature-icon">🔒</span>
                  <div className="feature-title">100% Local First</div>
                  <div className="feature-sub">Zero telemetry. Runs completely on your local Ollama instance.</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Composer */}
        <Composer
          busy={busy}
          statusLine={statusLine}
          onSend={onSend}
          onStop={onStop}
          activeModel={activeModel}
          recallOn={recallOn}
          onToggleRecall={onToggleRecall}
          hasMessages={hasMessages}
        />
      </div>

      {/* In-Chat Memory & Context Drawer */}
      {showMemoryDrawer && (
        <aside className="in-chat-memory-drawer">
          <div className="drawer-head">
            <div className="drawer-title">
              <span>🧠 Memory &amp; Context Drawer</span>
            </div>
            <button className="drawer-close-btn" onClick={() => setShowMemoryDrawer(false)}>×</button>
          </div>

          {/* Quick Fact Creator */}
          <div className="quick-fact-box">
            <label className="quick-fact-label">Teach MemOS a new fact:</label>
            <div className="quick-fact-row">
              <input
                type="text"
                placeholder="e.g. User prefers Python and FastAPI..."
                value={quickFact}
                onChange={(e) => setQuickFact(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAddQuickFact();
                }}
              />
              <button
                className="btn-quick-add"
                disabled={!quickFact.trim()}
                onClick={handleAddQuickFact}
              >
                + Add
              </button>
            </div>
          </div>

          {/* Memory Search */}
          <div className="drawer-search">
            <input
              type="text"
              placeholder="Search active memories…"
              value={memSearchQuery}
              onChange={(e) => setMemSearchQuery(e.target.value)}
            />
          </div>

          {/* Memory List */}
          <div className="drawer-memory-list">
            {filteredMemories.length === 0 ? (
              <div className="drawer-empty">
                {memSearchQuery ? "No matching memories found." : "No memories stored yet."}
              </div>
            ) : (
              filteredMemories.map((m) => {
                const imp = m.importance_score != null ? m.importance_score : 1.0;
                const impPct = Math.min(100, Math.round((imp / 2.0) * 100));
                const recalled = activeRecalledMap.get(m.id) || activeRecalledMap.get((m.content || "").toLowerCase().trim());
                const isMuted = (m.tags || []).includes("mute_recall");
                const lastUsedStr = formatRelativeTime(m.lastAccessed || m.createdAt || m.updatedAt);
                const sourceLabel = m.project ? `📁 ${m.project}` : (m.source === "chat" || m.source === "chat_analysis" ? "💬 Chat" : "✍ Manual");

                return (
                  <div key={m.id} className={"drawer-memory-item" + (m.pinned ? " pinned" : "") + (isMuted ? " muted" : "")}>
                    <div className="d-mem-top">
                      <button
                        className={"d-pin-btn" + (m.pinned ? " on" : "")}
                        onClick={() => onMemPin && onMemPin(m.id, !m.pinned)}
                        title={m.pinned ? "Unpin memory" : "Pin memory (always inject in context)"}
                      >
                        {m.pinned ? "📌" : "○"}
                      </button>
                      <button
                        className={"d-mute-btn" + (isMuted ? " muted" : "")}
                        onClick={() => onMemToggleMute && onMemToggleMute(m.id)}
                        title={isMuted ? "Unmute memory (enable prompt recall)" : "Mute memory (exclude from prompt recall)"}
                      >
                        {isMuted ? "🔕" : "🔔"}
                      </button>
                      <span className="d-mem-text" style={{ opacity: isMuted ? 0.65 : 1 }}>
                        {m.content}
                      </span>
                      <button
                        className="d-del-btn"
                        onClick={() => onMemDelete && onMemDelete(m.id)}
                        title="Delete memory"
                      >
                        ×
                      </button>
                    </div>

                    {/* Recalled in current conversation indicator */}
                    {recalled && (
                      <div className="d-recalled-tag" title="Injected into recent prompt context">
                        <span>🎯 Recalled</span>
                        {recalled.relevance_score != null && (
                          <span>· {Math.round(recalled.relevance_score * 100)}% match</span>
                        )}
                      </div>
                    )}

                    {isMuted && !recalled && (
                      <div className="d-muted-tag">
                        <span>🔕 Muted from recall</span>
                      </div>
                    )}

                    {/* Meta row: Last used timestamp & source */}
                    <div className="d-mem-meta">
                      <span className="d-mem-time" title={m.lastAccessed ? new Date(m.lastAccessed).toLocaleString() : ""}>
                        🕒 {lastUsedStr}
                      </span>
                      <span className="d-mem-source">
                        {sourceLabel}
                      </span>
                    </div>

                    <div className="d-mem-footer">
                      <div className="d-tags">
                        {(m.tags || []).filter((t) => t !== "mute_recall").map((t) => (
                          <span key={t} className="d-tag">#{t}</span>
                        ))}
                      </div>
                      <div className="d-gauge-wrap" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span className="d-imp-label">{imp.toFixed(2)}</span>
                        <div className="d-gauge" title={`Importance score: ${imp.toFixed(2)}`}>
                          <div className="d-gauge-fill" style={{ width: `${impPct}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>
      )}
    </div>
  );
}