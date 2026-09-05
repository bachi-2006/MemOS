import { EMBEDDING_HINT } from "../lib/util.js";

export default function Topbar({
  title,
  recallOn,
  topK,
  models,
  activeModel,
  onModelChange,
  onSettings,
  onExport,
  onImportClick,
  theme,
  onTheme,
  onMenu,
}) {
  const chatModels = models.filter((m) => !EMBEDDING_HINT.test(m.name));
  const embModels = models.filter((m) => EMBEDDING_HINT.test(m.name));

  return (
    <header className="topbar">
      <button className="menu-btn" id="menuBtn" aria-label="Toggle sidebar" onClick={onMenu}>
        &#9776;
      </button>
      <div className="conv-title" id="convTitle">{title}</div>
      <span className="sp" />
      <span
        className={"recall-badge" + (recallOn ? " on" : "")}
        id="recallBadge"
        title="Memory recall status"
      >
        <span className="kd" />
        <span id="recallBadgeText">{recallOn ? "recall · " + topK : "memory off"}</span>
      </span>
      <select
        id="modelSelect"
        aria-label="Active model"
        value={activeModel || ""}
        onChange={(e) => onModelChange(e.target.value)}
      >
        {chatModels.map((m) => (
          <option key={m.name} value={m.name}>{m.name}</option>
        ))}
        {embModels.length ? (
          <optgroup label="embedding only">
            {embModels.map((m) => (
              <option key={m.name} value={m.name} disabled>
                {m.name} (embeddings)
              </option>
            ))}
          </optgroup>
        ) : null}
      </select>
      <button id="settingsBtn" className="btn small" onClick={onSettings}>Settings</button>
      <button id="exportBtn" className="btn small" title="Export this conversation to a JSON file" onClick={onExport}>
        Export
      </button>
      <button id="importBtn" className="btn small" title="Import a conversation from JSON" onClick={onImportClick}>
        Import
      </button>
      <button id="themeBtn" className="btn small" title="Toggle light/dark theme" onClick={onTheme}>
        {theme === "light" ? "Dark" : "Light"}
      </button>
    </header>
  );
}