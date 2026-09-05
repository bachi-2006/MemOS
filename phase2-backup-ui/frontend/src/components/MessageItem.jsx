import { useState } from "react";
import { renderMarkdown } from "../lib/markdown.js";
import { fmtMeta } from "../lib/util.js";

function Mini({ label, onClick, disabled, title }) {
  return (
    <button className="mini" disabled={disabled} title={title} onClick={onClick}>
      {label}
    </button>
  );
}

export default function MessageItem({ m, streamingBusy, onRegenerate }) {
  const [open, setOpen] = useState(false);
  const isStreaming = !!m.streaming;

  if (m.role === "user") {
    return (
      <div className="msg user">
        <div className="who">you</div>
        <div className="body">
          <div className="bubble">{m.content}</div>
          <div className="meta">{fmtMeta(m)}</div>
          <div className="msg-actions">
            <Mini label="Copy" onClick={() => navigator.clipboard && navigator.clipboard.writeText(m.content)} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={"msg assistant" + (isStreaming ? " streaming" : "")}>
      <div className="who">assistant</div>
      <div className="body">
        {m.reasoning ? (
          <div
            className={"reasoning" + (isStreaming || open ? " open" : "")}
          >
            <button
              className="reasoning-toggle"
              aria-expanded={isStreaming || open ? "true" : "false"}
              onClick={() => setOpen(!open)}
            >
              thinking
            </button>
            <div className="reasoning-body">{m.reasoning}</div>
          </div>
        ) : null}

        <div
          className="bubble"
          dangerouslySetInnerHTML={{
            __html: renderMarkdown(m.content || "") + (isStreaming ? '<span class="cursor"></span>' : ""),
          }}
        />

        <div className="msg-actions">
          <Mini label="Copy" onClick={() => navigator.clipboard && navigator.clipboard.writeText(m.content)} />
          <Mini label="Regenerate" disabled={streamingBusy} onClick={onRegenerate} />
          {!isStreaming && m.meta ? <span className="meta">{fmtMeta(m)}</span> : null}
        </div>
      </div>
    </div>
  );
}