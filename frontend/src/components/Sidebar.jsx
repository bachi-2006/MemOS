import { useState, useMemo } from "react";
import { EMBEDDING_HINT, fmtBytes } from "../lib/util.js";
import MemoryView from "./MemoryView.jsx";
import SetupView from "./SetupView.jsx";

function ChatPanel({
  sessions = [],
  currentId = null,
  onNewChat,
  onSelect,
  onDelete,
  models = [],
  loadedModels = [],
  activeModel = "",
  onSelectModel,
  online = null,
  statusText = "",
  onRefreshModels,
}) {
  const [chatSearch, setChatSearch] = useState("");
  const safeSessions = Array.isArray(sessions) ? sessions : [];
  const safeModels = Array.isArray(models) ? models : [];
  const safeLoaded = Array.isArray(loadedModels) ? loadedModels : [];

  const filteredSessions = useMemo(() => {
    if (!chatSearch.trim()) return safeSessions;
    const q = chatSearch.toLowerCase();
    return safeSessions.filter(
      (s) =>
        (s.title || "").toLowerCase().includes(q) ||
        (Array.isArray(s.messages) &&
          s.messages.some((m) => (m.content || "").toLowerCase().includes(q)))
    );
  }, [safeSessions, chatSearch]);

  return (
    <div className="side-view active" id="viewChat">
      <div className="side-row">
        <button id="newChat" className="btn primary block" onClick={onNewChat}>
          + New conversation
        </button>
      </div>
      <div className="side-section-title">Conversations</div>
      {safeSessions.length > 2 && (
        <div className="sidebar-search-box">
          <input
            type="text"
            placeholder="Search chats…"
            value={chatSearch}
            onChange={(e) => setChatSearch(e.target.value)}
            className="sidebar-search-input"
          />
          {chatSearch && (
            <button
              className="sidebar-search-clear"
              onClick={() => setChatSearch("")}
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>
      )}
      <nav className="sessions" aria-label="Conversations">
        {filteredSessions.length === 0 ? (
          <div style={{ padding: "10px 8px", color: "var(--muted)", fontSize: 12 }}>
            {chatSearch ? "No matching chats found." : "No conversations yet."}
          </div>
        ) : (
          filteredSessions.map((s, i) => (
            <button
              key={s.id}
              className={"session" + (s.id === currentId ? " active" : "")}
              role="tab"
              aria-selected={s.id === currentId ? "true" : "false"}
              onClick={() => onSelect(s.id)}
            >
              <span className="t">{s.title || "Untitled chat"}</span>
              <span className="n">{i + 1}</span>
              <span
                className="del"
                title="Delete"
                role="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(s.id);
                }}
              >
                &#10005;
              </span>
            </button>
          ))
        )}
      </nav>
      <div className="side-section">
        <div className="side-head">
          <span>Installed models</span>
          <button className="icon-btn" title="Refresh model list" onClick={onRefreshModels}>
            &#8635;
          </button>
        </div>
        <div className="model-list">
          {safeModels.length === 0 ? (
            <div style={{ padding: "8px 10px", fontSize: 11, color: "var(--muted)" }}>
              {online === false ? "Ollama offline" : "No models found"}
            </div>
          ) : (
            safeModels.map((m) => {
              const isEmbed = EMBEDDING_HINT.test(m.name);
              const loaded = safeLoaded.includes(m.name);
              return (
                <button
                  key={m.name}
                  className={"model-item" + (m.name === activeModel ? " active" : "")}
                  onClick={() => !isEmbed && onSelectModel && onSelectModel(m.name)}
                >
                  <span className={"ld" + (loaded ? " on" : "")} />
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <div className="nm">{m.name}{isEmbed ? " (embed)" : ""}</div>
                    <div className="meta">{[m.params, m.quant, fmtBytes(m.size)].filter(Boolean).join(" · ")}</div>
                  </span>
                  {loaded ? <span className="io">loaded</span> : null}
                </button>
              );
            })
          )}
        </div>
      </div>
      <div className="side-foot">
        <span className={"dot " + (online === null ? "" : online ? "on" : "off")} />
        <span>{online === null ? "checking" : statusText}</span>
      </div>
    </div>
  );
}

export default function Sidebar({
  tab = "chat",
  onTab,
  sessionCount = 0,
  memStats = { total: 0, active: 0, pinned: 0, conflict: 0 },
  memItems = [],
  memBusy = "",
  memEngine = "",
  onMemAdd,
  onMemOptimize,
  onMemClear,
  onMemPin,
  onMemDelete,
  onNewChat,
  selectSession,
  deleteSession,
  sessions = [],
  currentId = null,
  models = [],
  loadedModels = [],
  activeModel = "",
  onSelectModel,
  online = null,
  statusText = "",
  onRefreshModels,
  settings = {},
  memConfig = {},
  embedModels = [],
  onSetting,
  onMemConfig,
}) {
  const handleSelectSession = (id) => {
    if (selectSession) selectSession(id);
    if (onTab) onTab("chat");
  };

  const handleNewChat = () => {
    if (onNewChat) onNewChat();
    if (onTab) onTab("chat");
  };

  return (
    <aside className="sidebar" id="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <div className="brand-logo">M</div>
          <div>
            <div className="brand-name">
              <em>MemOS</em> · <span>Studio</span>
            </div>
            <div className="brand-sub">Cognitive Memory Companion</div>
          </div>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="side-nav-tabs" role="tablist">
        <button
          className={"side-nav-btn" + (tab === "chat" ? " active" : "")}
          id="tabChat"
          role="tab"
          aria-selected={tab === "chat"}
          onClick={() => onTab("chat")}
          title="Interactive Chat"
        >
          <span className="nav-icon">💬</span>
          <span className="nav-text">Chat</span>
          {sessionCount > 0 && <span className="nav-badge">{sessionCount}</span>}
        </button>

        <button
          className={"side-nav-btn" + (tab === "memory" ? " active" : "")}
          id="tabMemory"
          role="tab"
          aria-selected={tab === "memory"}
          onClick={() => onTab("memory")}
          title="Long-Term Memory Bank"
        >
          <span className="nav-icon">🧠</span>
          <span className="nav-text">Memory</span>
          {memStats?.total > 0 && <span className="nav-badge">{memStats.total}</span>}
        </button>

        <button
          className={"side-nav-btn" + (tab === "graph" ? " active" : "")}
          id="tabGraph"
          role="tab"
          aria-selected={tab === "graph"}
          onClick={() => onTab("graph")}
          title="Knowledge Graph"
        >
          <span className="nav-icon">🕸️</span>
          <span className="nav-text">Graph</span>
        </button>

        <button
          className={"side-nav-btn" + (tab === "dashboard" ? " active" : "")}
          id="tabDashboard"
          role="tab"
          aria-selected={tab === "dashboard"}
          onClick={() => onTab("dashboard")}
          title="System Health & Analytics"
        >
          <span className="nav-icon">📊</span>
          <span className="nav-text">Health</span>
        </button>

        <button
          className={"side-nav-btn" + (tab === "profile" ? " active" : "")}
          id="tabProfile"
          role="tab"
          aria-selected={tab === "profile"}
          onClick={() => onTab("profile")}
          title="User Persona & Continuous Profile"
        >
          <span className="nav-icon">👤</span>
          <span className="nav-text">Profile</span>
        </button>

        <button
          className={"side-nav-btn" + (tab === "setup" ? " active" : "")}
          id="tabSettings"
          role="tab"
          aria-selected={tab === "setup"}
          onClick={() => onTab("setup")}
          title="Engine Configuration"
        >
          <span className="nav-icon">⚙️</span>
          <span className="nav-text">Setup</span>
        </button>
      </div>

      {/* Main Sidebar Content: Always shows sessions & models for fast navigation */}
      <ChatPanel
        sessions={sessions}
        currentId={currentId}
        onNewChat={handleNewChat}
        onSelect={handleSelectSession}
        onDelete={deleteSession}
        models={models}
        loadedModels={loadedModels}
        activeModel={activeModel}
        onSelectModel={onSelectModel}
        online={online}
        statusText={statusText}
        onRefreshModels={onRefreshModels}
      />
    </aside>
  );
}