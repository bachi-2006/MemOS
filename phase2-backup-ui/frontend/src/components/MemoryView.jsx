import { useEffect, useState } from "react";

function MemTag({ text, conflict, strong }) {
  const cls = ["mem-tag"];
  if (conflict) cls.push("conflict");
  if (strong) cls.push("strong");
  return <span className={cls.join(" ")}>{text}</span>;
}

export default function MemoryView({
  items,
  stats,
  busy,
  engineStatus,
  onAdd,
  onOptimize,
  onClearAll,
  onPin,
  onDelete,
}) {
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    const clear = () => {
      setAdding(false);
      setDraft("");
    };
    const onKey = (e) => {
      if (e.key === "Escape") clear();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = items
    .slice()
    .sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0) || (b.importance_score || 0) - (a.importance_score || 0))
    .filter((m) => {
      if (!query) return true;
      return (m.content + " " + (m.tags || []).join(" ")).toLowerCase().includes(query.toLowerCase());
    });

  const save = async () => {
    if (!draft.trim()) return;
    const it = await onAdd(draft.trim());
    if (it) {
      setDraft("");
      setAdding(false);
    }
  };

  return (
    <div className="side-view active" id="viewMemory">
      <div className="memory-head">
        <div className="mem-stats">
          <div className="mem-stat"><div className="v">{stats.total}</div><div className="l">Memories</div></div>
          <div className="mem-stat"><div className="v">{stats.active}</div><div className="l">Active</div></div>
          <div className="mem-stat"><div className="v">{stats.pinned}</div><div className="l">Pinned</div></div>
          <div className={"mem-stat" + (stats.conflict ? " conflict" : "")}><div className="v">{stats.conflict}</div><div className="l">Conflicts</div></div>
        </div>
        <input
          className="mem-search"
          type="text"
          placeholder="Search memories…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="mem-toolbar">
          <button className="btn small" onClick={() => setAdding(!adding)}>+ Add</button>
          <button className="btn small" title="Compress old memories & forget stale ones" disabled={!!busy} onClick={onOptimize}>
            Optimize
          </button>
        </div>
        {adding ? (
          <div style={{ paddingBottom: 8 }}>
            <textarea
              className="mem-search"
              rows="2"
              placeholder="What should I remember?"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  save();
                }
              }}
            />
            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn small primary" style={{ flex: 1 }} onClick={save}>Save memory</button>
              <button className="btn small" style={{ flex: 1 }} onClick={() => { setAdding(false); setDraft(""); }}>
                Cancel
              </button>
            </div>
          </div>
        ) : null}
        {busy ? <div className="mem-busy">{busy}</div> : null}
      </div>

      <div className="mem-list" id="memList">
        {!filtered.length ? (
          <div className="mem-empty">
            {query
              ? "No memories match that search."
              : "No memories yet. Ask a question or enable auto-extraction and each conversation will teach you here."}
          </div>
        ) : (
          filtered.map((m) => (
            <div
              key={m.id}
              className={
                "mem-item" +
                (m.pinned ? " pinned" : "") +
                (m.conflict ? " conflict" : "") +
                (m.status === "forgotten" ? " forgotten" : "")
              }
            >
              <div className="mem-top">
                <button
                  className={"mem-pin" + (m.pinned ? " on" : "")}
                  title={m.pinned ? "Unpin" : "Pin (always recalled)"}
                  onClick={() => onPin(m.id, !m.pinned)}
                >
                  {m.pinned ? "📌" : "○"}
                </button>
                <div className="mem-text">{m.content}</div>
              </div>
              <div className="mem-tags">
                {(m.tags || []).map((t) => (
                  <MemTag key={t} text={t} conflict={t === "conflict_flagged" || (m.conflict && t === "fact")} strong={false} />
                ))}
                {m.conflict ? <MemTag text="conflict" conflict /> : null}
                {m.status !== "active" ? <MemTag text={m.status} /> : null}
              </div>
              <div className="mem-bar-row">
                <span className="mem-imp-label">
                  importance {(m.importance_score != null ? m.importance_score : 1).toFixed(2)}
                </span>
                <div className="mem-imp">
                  <span
                    className={
                      m.importance_score != null && m.importance_score >= 0.8
                        ? "imp-hi"
                        : m.importance_score != null && m.importance_score <= 0.4
                          ? "imp-low"
                          : ""
                    }
                    style={{ width: Math.min(100, Math.round((m.importance_score != null ? m.importance_score : 1) * 40)) + "%" }}
                  />
                </div>
              </div>
              <div className="mem-foot">
                <span className="mem-act">confidence {(m.confidence != null ? m.confidence : 1).toFixed(2)}</span>
                <button className="mem-act danger" onClick={() => onDelete(m.id)}>delete</button>
              </div>
              {m.conflict && m.conflictInfo ? (
                <div style={{ fontSize: 11, color: "var(--danger)", marginTop: 6, wordBreak: "break-word" }}>
                  ⚠ {m.conflictInfo}
                </div>
              ) : null}
            </div>
          ))
        )}
      </div>

      <div className="side-foot">
        <span className="mem-act" style={{ border: "none" }} onClick={onClearAll}>Clear &amp; reset</span>
        <span className="sp" />
        <span style={{ fontSize: 11, color: "var(--faint)" }}>{engineStatus}</span>
      </div>
    </div>
  );
}