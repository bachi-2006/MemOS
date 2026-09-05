import { EMBEDDING_HINT, fmtBytes } from "../lib/util.js";
import MemoryView from "./MemoryView.jsx";
import SetupView from "./SetupView.jsx";

function ChatPanel({
  sessions,
  currentId,
  onNewChat,
  onSelect,
  onDelete,
  models,
  loadedModels,
  activeModel,
  onSelectModel,
  online,
  statusText,
  onRefreshModels,
}) {
  return (
    <div className="side-view active" id="viewChat">
      <div className="side-row">
        <button id="newChat" className="btn primary block" onClick={onNewChat}>
          New conversation
        </button>
      </div>
      <nav className="sessions" aria-label="Conversations">
        {sessions.length === 0 ? (
          <div style={{ padding: 10, color: "var(--muted)", fontSize: 12 }}>
            No conversations yet.
          </div>
        ) : (
          sessions.map((s, i) => (
            <button
              key={s.id}
              className={"session" + (s.id === currentId ? " active" : "")}
              role="tab"
              aria-selected={s.id === currentId ? "true" : "false"}
              onClick={() => onSelect(s.id)}
            >
              <span className="t">{s.title}</span>
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
          {models.map((m) => {
            const isEmbed = EMBEDDING_HINT.test(m.name);
            const loaded = loadedModels.includes(m.name);
            return (
              <button
                key={m.name}
                className={"model-item" + (m.name === activeModel ? " active" : "")}
                onClick={() => !isEmbed && onSelectModel(m.name)}
              >
                <span className={"ld" + (loaded ? " on" : "")} />
                <span style={{ flex: 1, minWidth: 0 }}>
                  <div className="nm">{m.name}{isEmbed ? " (embed)" : ""}</div>
                  <div className="meta">{[m.params, m.quant, fmtBytes(m.size)].filter(Boolean).join(" · ")}</div>
                </span>
                {loaded ? <span className="io">loaded</span> : null}
              </button>
            );
          })}
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
  tab,
  onTab,
  sessionCount,
  memStats,
  memItems,
  memBusy,
  memEngine,
  onMemAdd,
  onMemOptimize,
  onMemClear,
  onMemPin,
  onMemDelete,
  onNewChat,
  selectSession,
  deleteSession,
  sessions,
  currentId,
  models,
  loadedModels,
  activeModel,
  onSelectModel,
  online,
  statusText,
  onRefreshModels,
  settings,
  memConfig,
  embedModels,
  onSetting,
  onMemConfig,
}) {
  return (
    <aside className="sidebar" id="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <div className="brand-logo">M</div>
          <div>
            <div className="brand-name">
              <em>qwen</em> — local
            </div>
            <div className="brand-sub">MemOS · phase 2 · full-stack build</div>
          </div>
        </div>
      </div>

      <div className="side-tabs" role="tablist">
        <button className={"side-tab" + (tab === "chat" ? " active" : "")} id="tabChat" role="tab" onClick={() => onTab("chat")}>
          Chat <span className="count">{sessionCount}</span>
        </button>
        <button className={"side-tab" + (tab === "memory" ? " active" : "")} id="tabMemory" role="tab" onClick={() => onTab("memory")}>
          Memory <span className="count">{memStats.total}</span>
        </button>
        <button className={"side-tab" + (tab === "setup" ? " active" : "")} id="tabSettings" role="tab" onClick={() => onTab("setup")}>
          Setup
        </button>
      </div>

      {tab === "chat" ? (
        <ChatPanel {...{
          sessions, currentId, onNewChat, onSelect: selectSession, onDelete: deleteSession,
          models, loadedModels, activeModel, onSelectModel,
          online, statusText, onRefreshModels,
        }} />
      ) : null}

      {tab === "memory" ? (
        <MemoryView
          items={memItems}
          stats={memStats}
          busy={memBusy}
          engineStatus={memEngine}
          onAdd={onMemAdd}
          onOptimize={onMemOptimize}
          onClearAll={onMemClear}
          onPin={onMemPin}
          onDelete={onMemDelete}
        />
      ) : null}

      {tab === "setup" ? (
        <SetupView
          settings={settings}
          memConfig={memConfig}
          embedModels={embedModels}
          onSetting={onSetting}
          onMemConfig={onMemConfig}
        />
      ) : null}
    </aside>
  );
}