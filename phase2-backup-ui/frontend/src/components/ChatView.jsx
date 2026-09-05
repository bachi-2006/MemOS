import { useEffect, useRef } from "react";
import MessageItem from "./MessageItem.jsx";
import Composer from "./Composer.jsx";

export default function ChatView({
  session,
  busy,
  statusLine,
  onSend,
  onStop,
  onRegenerate,
}) {
  const scrollRef = useRef(null);
  const stickRef = useRef(true);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [session?.messages]);

  return (
    <>
      <div className="messages" id="messages" ref={scrollRef} onScroll={onScroll}>
        {session && session.messages && session.messages.length ? (
          <div className="messages-inner">
            {session.messages.map((m) => (
              <MessageItem key={m.id} m={m} streamingBusy={busy} onRegenerate={onRegenerate} />
            ))}
          </div>
        ) : (
          <div className="empty">
            <div className="empty-card">
              <b>No active conversation.</b>
              <br />
              Start a new one or send a message.
              <br />
              Everything stays local-first — worth it.
              <br />
              <br />
              <span className="empty-kbd">Enter</span> send ·{" "}
              <span className="empty-kbd">Shift+Enter</span> newline ·{" "}
              <span className="empty-kbd">Esc</span> stop
            </div>
          </div>
        )}
      </div>
      <Composer busy={busy} statusLine={statusLine} onSend={onSend} onStop={onStop} />
    </>
  );
}