function Field({ label, children, style }) {
  return (
    <div className="field" style={style}>
      <label>{label}</label>
      {children}
    </div>
  );
}

export default function SetupView({
  settings,
  memConfig,
  embedModels,
  onSetting,
  onMemConfig,
}) {
  const set = (key) => (e) => onSetting(key, e.target.value);
  const setMem = (key) => (e) => onMemConfig(key, e.target.value);

  return (
    <div className="side-view active" id="viewSettings">
      <div className="memory-head">
        <div className="side-head" style={{ padding: "0 2px 8px" }}>
          <span>Chat parameters</span>
        </div>
        <Field label="Compute">
          <select id="gu" value={settings.compute} onChange={set("compute")}>
            <option value="cpu">CPU (num_gpu 0)</option>
            <option value="gpu">GPU</option>
          </select>
        </Field>
        <Field label="Temperature (2)" style={{ marginTop: 10 }}>
          <div className="range-row">
            <input
              type="range"
              id="tp"
              min="0"
              max="2"
              step="0.1"
              value={settings.temp}
              onChange={(e) => {
                onSetting("temp", Number(e.target.value));
              }}
            />
            <span className="val">{Number(settings.temp).toFixed(1)}</span>
          </div>
        </Field>
        <Field label="Max tokens" style={{ marginTop: 10 }}>
          <input type="number" id="np" min="0" max="8192" value={settings.numPredict} onChange={set("numPredict")} />
        </Field>
        <Field label="Context (last N messages)" style={{ marginTop: 10 }}>
          <input type="number" id="nw" min="1" max="64" value={settings.windowN} onChange={set("windowN")} />
        </Field>
        <Field label="Thinking (qwen3 deep-reasoning)" style={{ marginTop: 10 }}>
          <select id="th" value={settings.thinking ? "on" : "off"} onChange={(e) => onSetting("thinking", e.target.value === "on")}>
            <option value="off">Off — faster, reliable output</option>
            <option value="on">On — show reasoning</option>
          </select>
        </Field>
        <Field label="System prompt" style={{ marginTop: 10 }}>
          <textarea id="sp" placeholder="Optional instructions for the model" value={settings.systemPrompt} onChange={set("systemPrompt")} />
        </Field>
        <Field label="Shortcuts" style={{ marginTop: 12 }}>
          <span className="shortcuts">
            <code>Enter</code> send · <code>Shift+Enter</code> newline · <code>Esc</code> stop · <code>Alt+R</code> regenerate ·{" "}
            <code>Ctrl+N</code> new chat · <code>Ctrl+1..9</code> switch conversation · <code>Ctrl+Enter</code> send
          </span>
        </Field>

        <div className="side-head" style={{ padding: "14px 2px 8px" }}>
          <span>Memory engine</span>
        </div>
        <Field label="Memory recall">
          <select id="memRecall" value={memConfig.recall} onChange={setMem("recall")}>
            <option value="on">On — inject relevant memories</option>
            <option value="off">Off</option>
          </select>
        </Field>
        <Field label="Auto-extract memories" style={{ marginTop: 10 }}>
          <select id="memExtract" value={memConfig.autoExtract} onChange={setMem("autoExtract")}>
            <option value="on">On — after each reply</option>
            <option value="off">Off</option>
          </select>
        </Field>
        <Field label="Embedding model" style={{ marginTop: 10 }}>
          <select id="memEmbed" value={memConfig.embedModel} onChange={setMem("embedModel")}>
            {embedModels.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </Field>
        <Field label="Top-K memories to recall" style={{ marginTop: 10 }}>
          <input type="number" id="memTopK" min="1" max="10" value={memConfig.topK} onChange={setMem("topK")} />
        </Field>
        <Field label="Compress memories older than (days)" style={{ marginTop: 10 }}>
          <input type="number" id="memCompressDays" min="7" max="180" value={memConfig.compressDays} onChange={setMem("compressDays")} />
        </Field>
      </div>
    </div>
  );
}