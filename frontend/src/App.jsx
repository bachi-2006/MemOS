import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import ChatView from "./components/ChatView.jsx";
import MemoryView from "./components/MemoryView.jsx";
import GraphView from "./components/GraphView.jsx";
import DashboardView from "./components/DashboardView.jsx";
import ProfileView from "./components/ProfileView.jsx";
import SetupView from "./components/SetupView.jsx";
import Toast from "./components/Toast.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { useMemory } from "./hooks/useMemory.js";
import { loadSettings, saveSettings, memCfg, THEME_KEY } from "./lib/config.js";
import { ollamaTags, ollamaPs } from "./lib/ollama.js";
import {
  fetchChats,
  fetchChatMessages,
  deleteChat as apiDeleteChat,
  streamChat,
} from "./lib/api.js";
import {
  memRefresh,
  memOptimizeNow,
  memAddManual,
  memDelete,
  memClear,
  memPin,
} from "./lib/memory.js";
import { uid, truncate, EMBEDDING_HINT } from "./lib/util.js";

const MEM_KEYS = {
  recall: "memos-recall",
  autoExtract: "memos-extract",
  embedModel: "memos-embed",
  topK: "memos-topk",
  compressDays: "memos-compress-days",
};

let toastTimer = 0;

export default function App() {
  const [settings, setSettings] = useState(() => loadSettings());
  const settingsRef = useRef(settings);
  useEffect(() => {
    settingsRef.current = settings;
    saveSettings(settings);
  }, [settings]);

  const [models, setModels] = useState([]);
  const [loadedModels, setLoadedModels] = useState([]);
  const [online, setOnline] = useState(null);
  const [tab, setTab] = useState("chat");
  const [busy, setBusy] = useState(false);
  const [memBusy, setMemBusy] = useState("");
  const [memEngine, setMemEngine] = useState("engine idle");
  const [statusLine, setStatusLine] = useState([]);
  const [toast, setToast] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || "light");
  const [memTick, setMemTick] = useState(0);

  const { items: memItems, stats: memStats } = useMemory();

  const streamRef = useRef(null);
  const fileRef = useRef(null);

  const current = settings.sessions.find((s) => s.id === settings.currentId) || null;

  const ctx = { activeModel: settings.activeModel, compute: settings.compute };
  const toggleMenu = () => document.body.classList.toggle("sidebar-open");

  /* ---------- status / toast ---------- */
  const pushStatus = (text, color, ttl) => {
    const id = uid();
    setStatusLine((sl) => [...sl.slice(-4), { id, text, color }]);
    if (ttl) {
      setTimeout(() => setStatusLine((sl) => sl.filter((x) => x.id !== id)), ttl);
    }
  };
  const showToast = (text) => {
    setToast({ text: String(text), key: uid() });
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => setToast(null), 3200);
  };

  /* ---------- model discovery ---------- */
  const refreshModels = async () => {
    try {
      const t = await ollamaTags();
      setModels(t);
      setOnline(true);
      return t;
    } catch {
      setOnline(false);
      return [];
    }
  };
  const refreshLoaded = async () => {
    try {
      const p = await ollamaPs();
      setLoadedModels(p.map((m) => m.model));
    } catch {}
  };

  /* ---------- session helpers ---------- */
  const newChat = () => {
    const id = uid();
    setSettings((s) => ({
      ...s,
      sessions: [{ id, title: "New chat", messages: [], isDraft: true, loaded: true }, ...s.sessions],
      currentId: id,
    }));
  };
  const selectSession = async (id) => {
    setSettings((s) => ({ ...s, currentId: id }));
    const sess = settingsRef.current.sessions.find((s) => s.id === id);
    if (sess && !sess.loaded && !sess.isDraft) {
      await loadSessionMessages(id);
    }
  };
  const loadSessionMessages = async (chatId) => {
    try {
      const msgs = await fetchChatMessages(chatId);
      if (Array.isArray(msgs)) {
        patchSession(chatId, (s) => ({
          ...s,
          loaded: true,
          messages: msgs.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            ts: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
          })),
        }));
      }
    } catch (e) {
      console.warn("Failed to load chat messages:", e);
    }
  };
  const deleteSession = async (id) => {
    try {
      await apiDeleteChat(id);
    } catch (e) {
      console.warn("Failed to delete chat on backend:", e);
    }
    setSettings((s) => {
      const sessions = s.sessions.filter((x) => x.id !== id);
      const currentId = s.currentId === id ? (sessions[0] ? sessions[0].id : null) : s.currentId;
      return { ...s, sessions, currentId };
    });
  };

  const pushMsg = (sid, msg) => {
    setSettings((s) => {
      const nextSessions = s.sessions.map((sess) =>
        sess.id === sid ? { ...sess, messages: [...(sess.messages || []), msg] } : sess
      );
      settingsRef.current = { ...s, sessions: nextSessions };
      return { ...s, sessions: nextSessions };
    });
  };
  const patchSession = (sid, fn) => {
    setSettings((s) => {
      const nextSessions = s.sessions.map((sess) => (sess.id === sid ? fn(sess) : sess));
      settingsRef.current = { ...s, sessions: nextSessions };
      return { ...s, sessions: nextSessions };
    });
  };
  const patchMessage = (sid, mid, fn) => {
    setSettings((s) => {
      const nextSessions = s.sessions.map((sess) =>
        sess.id === sid
          ? { ...sess, messages: (sess.messages || []).map((m) => (m.id === mid ? fn(m) : m)) }
          : sess
      );
      settingsRef.current = { ...s, sessions: nextSessions };
      return { ...s, sessions: nextSessions };
    });
  };
  const ensureTitle = (sid, text) => {
    const sess = settingsRef.current.sessions.find((x) => x.id === sid);
    if (sess && !sess.title && text) {
      patchSession(sid, (ss) => ({ ...ss, title: truncate(text, 34) }));
    }
  };

  /* ---------- streaming ---------- */
  const streamTurn = async (sess, promptText, userMsgId) => {
    const activeModel = settingsRef.current.activeModel;
    if (!activeModel) {
      pushStatus("select a model first", "#ef4444", 2800);
      return;
    }
    let sid = sess.id;
    const mid = uid();
    const acc = { text: "", firstTok: false };
    pushMsg(sid, {
      id: mid,
      role: "assistant",
      content: "",
      meta: activeModel,
      ts: Date.now(),
      streaming: true,
    });
    setBusy(true);
    setMemEngine(activeModel + " · streaming");

    const ctrl = new AbortController();
    streamRef.current = { ctrl, sid, mid, acc };
    let aborted = false;

    let tick = setInterval(() => {
      if (acc.firstTok) return;
      const count = (Math.floor(Date.now() / 500) % 3) + 1;
      const dots = ".".repeat(Math.max(1, Math.min(3, count)));
      patchMessage(sid, mid, (m) => ({ ...m, content: "…" + dots, streaming: true }));
    }, 600);

    let flushTimer = null;
    const flush = () => {
      if (flushTimer) return;
      flushTimer = setTimeout(() => {
        flushTimer = null;
        patchMessage(sid, mid, (m) => ({ ...m, content: acc.text }));
      }, 80);
    };

    let confirmedChatId = sess.isDraft ? null : sess.id;

    try {
      await streamChat({
        chatId: sess.isDraft ? undefined : sess.id,
        prompt: promptText,
        model: activeModel,
        personalized: memCfg.recall,
        signal: ctrl.signal,
        onContext: (ctxData) => {
          if (ctxData.chat_id) confirmedChatId = ctxData.chat_id;
          if (ctxData.recalled_memories && ctxData.recalled_memories.length) {
            patchMessage(sid, userMsgId, (m) => ({
              ...m,
              recalledMemories: ctxData.recalled_memories,
            }));
            pushStatus(`memories recalled · ${ctxData.recalled_memories.length}`, "#4f46e5", 2800);
          }
        },
        onToken: (tok, chatId) => {
          clearInterval(tick);
          acc.firstTok = true;
          acc.text += tok;
          if (chatId) confirmedChatId = chatId;
          flush();
        },
        onDone: (doneData) => {
          if (doneData.chat_id) confirmedChatId = doneData.chat_id;
        },
        onError: (err) => {
          throw err;
        },
      });

      clearInterval(tick);
      clearTimeout(flushTimer);
      patchMessage(sid, mid, (m) => ({
        ...m,
        content: acc.text,
        streaming: false,
      }));

      // If this was a draft session and backend assigned a chat_id, migrate local state
      if (confirmedChatId && confirmedChatId !== sid) {
        const oldId = sid;
        const newId = confirmedChatId;
        setSettings((s) => {
          const updatedSessions = s.sessions.map((sessItem) =>
            sessItem.id === oldId
              ? { ...sessItem, id: newId, isDraft: false, loaded: true }
              : sessItem
          );
          return {
            ...s,
            sessions: updatedSessions,
            currentId: s.currentId === oldId ? newId : s.currentId,
          };
        });
        sid = newId;
      }

      setMemEngine(activeModel + " · synchronized");
      pushStatus("memory · updated by backend", "#10b981", 2400);

      // Refresh memory store from backend after background analysis completes
      setTimeout(() => memRefresh(), 1500);
      setTimeout(() => memRefresh(), 4000);
    } catch (err) {
      clearInterval(tick);
      clearTimeout(flushTimer);
      if (err && err.name === "AbortError") {
        aborted = true;
        patchMessage(sid, mid, (m) => ({ ...m, content: acc.text, streaming: false }));
      } else {
        patchMessage(sid, mid, (m) => ({
          ...m,
          content: acc.text || "⚠ Something went wrong — is the MemOS backend connected?",
          streaming: false,
          meta: (m.meta || "") + " · error",
        }));
      }
    } finally {
      setBusy(false);
      streamRef.current = null;
    }
  };

  /* ---------- actions ---------- */
  const send = async (raw) => {
    const text = raw.trim();
    if (!text || busy) return;
    let sid = settingsRef.current.currentId;
    let sess = settingsRef.current.sessions.find((x) => x.id === sid);
    if (!sess) {
      const id = uid();
      const newSess = { id, title: "", messages: [], isDraft: true, loaded: true };
      const nextSessions = [newSess, ...settingsRef.current.sessions];
      settingsRef.current = { ...settingsRef.current, sessions: nextSessions, currentId: id };
      setSettings((s) => ({
        ...s,
        sessions: nextSessions,
        currentId: id,
      }));
      sid = id;
      sess = newSess;
    }
    const userMsg = { id: uid(), role: "user", content: text, ts: Date.now() };
    pushMsg(sid, userMsg);
    ensureTitle(sid, text);
    setStatusLine([]);

    if (!settingsRef.current.activeModel) {
      const name = await autoPickModel();
      if (name) {
        settingsRef.current = { ...settingsRef.current, activeModel: name };
        setSettings((s) => ({ ...s, activeModel: name }));
      }
    }

    await streamTurn(sess, text, userMsg.id);
  };

  const autoPickModel = async () => {
    const t = await refreshModels();
    const first = t.find((m) => !EMBEDDING_HINT.test(m.name));
    if (first) pushStatus("auto-selected " + first.name, "#00c896", 2600);
    return first ? first.name : "";
  };

  const stop = () => {
    if (streamRef.current && streamRef.current.ctrl) streamRef.current.ctrl.abort();
  };

  const regenerate = async () => {
    if (busy) return;
    const sid = settingsRef.current.currentId;
    const sess = settingsRef.current.sessions.find((x) => x.id === sid);
    if (!sess) return;
    const msgs = (sess.messages || []).filter((m) => !m.streaming);
    let lastUser = -1;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "user") {
        lastUser = i;
        break;
      }
    }
    if (lastUser < 0) return;
    const userMsg = msgs[lastUser];
    const truncated = msgs.slice(0, lastUser + 1);
    patchSession(sid, (ss) => ({ ...ss, messages: truncated }));
    await streamTurn(sess, userMsg.content, userMsg.id);
  };

  /* ---------- memory ---------- */
  const optimize = async () => {
    if (memBusy) return;
    setMemBusy("Optimizing…");
    setMemEngine("optimizing memory…");
    try {
      const r = await memOptimizeNow(ctx);
      setMemEngine(
        (r.archived ? r.archived + " archived" : "nothing to archive") +
          (r.forgotten ? " · " + r.forgotten + " forgotten" : "")
      );
      pushStatus("memory · " + (r.archived ? r.archived + " archived" : "nothing to archive"), "#00c896", 3000);
    } catch (e) {
      setMemEngine("optimize failed");
      console.error(e);
    }
    setMemBusy("");
  };
  const addManual = async (content) => {
    setMemBusy("Embedding…");
    const it = await memAddManual(content);
    setMemBusy("");
    if (it) {
      setMemEngine("memory saved");
      pushStatus("memory saved ✓", "#00c896", 2600);
    } else {
      setMemEngine("nothing to save");
    }
    return it;
  };

  /* ---------- import / export ---------- */
  const exportChat = () => {
    const s = settingsRef.current;
    const blob = new Blob(
      [JSON.stringify({ app: "memOS", exportedAt: new Date().toISOString(), sessions: s.sessions }, null, 2)],
      { type: "application/json" }
    );
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "memOS-conversation.json";
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const importFile = async (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      const incoming = Array.isArray(data.sessions) ? data.sessions : [data];
      const clean = incoming
        .filter((s) => s && Array.isArray(s.messages))
        .map((s) => ({
          id: s.id || uid(),
          title: s.title || s.messages.find((m) => m.role === "user")?.content?.slice(0, 34) || "Imported",
          messages: s.messages.map((m) => ({ ...m, streaming: false })),
        }));
      if (!clean.length) throw new Error("no sessions");
      const existing = new Set((settingsRef.current.sessions || []).map((x) => x.id));
      const merged = clean.filter((s) => !existing.has(s.id)).concat(settingsRef.current.sessions || []);
      setSettings((st) => ({
        ...st,
        sessions: merged,
        currentId: clean[clean.length - 1].id,
      }));
      showToast("Imported " + clean.length + " conversation" + (clean.length > 1 ? "s" : "") + ".");
    } catch (err) {
      showToast("Import failed: invalid JSON.");
    }
  };

  /* ---------- setup ---------- */
  const onSetting = (key, value) => setSettings((s) => ({ ...s, [key]: value }));
  const onMemConfig = (key, value) => {
    const lk = MEM_KEYS[key];
    if (lk) localStorage.setItem(lk, String(value));
    setMemTick((t) => t + 1);
  };

  /* ---------- theme ---------- */
  const toggleTheme = () => {
    setTheme((t) => {
      const nt = t === "light" ? "dark" : "light";
      localStorage.setItem(THEME_KEY, nt);
      return nt;
    });
  };
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  /* ---------- boot ---------- */
  useEffect(() => {
    const boot = async () => {
      await refreshLoaded();
      const t = await refreshModels();
      if (t.length) {
        setOnline(true);
        const s = settingsRef.current;
        if (!s.activeModel || !t.find((m) => m.name === s.activeModel)) {
          const first = t.find((m) => !EMBEDDING_HINT.test(m.name));
          if (first) setSettings((st) => ({ ...st, activeModel: first.name }));
        }
      }

      // Load chats from backend Single Source of Truth
      try {
        const backendChats = await fetchChats();
        if (Array.isArray(backendChats) && backendChats.length > 0) {
          const formatted = backendChats.map((c) => ({
            id: c.id,
            title: c.title || "Chat session",
            messages: [],
            loaded: false,
          }));
          const targetId = formatted[0].id;
          setSettings((st) => ({
            ...st,
            sessions: formatted,
            currentId: targetId,
          }));
          loadSessionMessages(targetId);
        } else {
          newChat();
        }
      } catch (err) {
        console.warn("Could not fetch backend chats on boot:", err);
        if (!settingsRef.current.sessions.length) {
          newChat();
        }
      }
    };
    boot();
    const iv = setInterval(refreshLoaded, 8000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---------- keyboard shortcuts ---------- */
  useEffect(() => {
    const onKey = (e) => {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "n") {
        e.preventDefault();
        newChat();
      } else if (mod && /^[1-9]$/.test(e.key)) {
        const idx = Number(e.key) - 1;
        const sess = settingsRef.current.sessions[idx];
        if (sess) selectSession(sess.id);
      } else if (e.altKey && e.key.toLowerCase() === "r") {
        e.preventDefault();
        regenerate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy]);

  /* ---------- render ---------- */
  const embedModels = models.filter((m) => EMBEDDING_HINT.test(m.name)).map((m) => m.name);
  const statusText = online === true ? "ollama · " + models.length + " models" : online === false ? "ollama offline" : "checking ollama…";

  return (
    <div className="app" id="app">
      <input ref={fileRef} type="file" accept=".json,application/json" style={{ display: "none" }} onChange={importFile} />
      <Sidebar
        tab={tab}
        onTab={setTab}
        sessionCount={settings.sessions.length}
        memStats={memStats}
        memItems={memItems}
        memBusy={memBusy}
        memEngine={memEngine}
        onMemAdd={addManual}
        onMemOptimize={optimize}
        onMemClear={() => { memClear(); setMemEngine("engine idle"); }}
        onMemPin={(id, pinned) => memPin(id, pinned)}
        onMemDelete={(id) => memDelete(id)}
        sessions={settings.sessions}
        currentId={settings.currentId}
        onNewChat={newChat}
        selectSession={selectSession}
        deleteSession={deleteSession}
        models={models}
        loadedModels={loadedModels}
        activeModel={settings.activeModel}
        onSelectModel={(name) => onSetting("activeModel", name)}
        online={online}
        statusText={statusText}
        onRefreshModels={() => { refreshModels(); refreshLoaded(); }}
        settings={settings}
        memConfig={{ ...memCfg, __tick: memTick }}
        embedModels={embedModels}
        onSetting={onSetting}
        onMemConfig={onMemConfig}
      />
      <main className="main">
        <Topbar
          title={
            tab === "chat"
              ? (current ? current.title || "New conversation" : "New conversation")
              : tab === "memory"
              ? "Long-Term Memory Bank"
              : tab === "graph"
              ? "Knowledge Graph & Synapse Visualizer"
              : tab === "dashboard"
              ? "System Health & Analytics"
              : tab === "profile"
              ? "User Persona & Preferences"
              : "Settings & Configuration"
          }
          recallOn={memCfg.recall}
          topK={memCfg.topK}
          models={models}
          activeModel={settings.activeModel}
          onModelChange={(name) => onSetting("activeModel", name)}
          onSettings={() => setTab("setup")}
          onExport={exportChat}
          onImportClick={() => fileRef.current && fileRef.current.click()}
          theme={theme}
          onTheme={toggleTheme}
          onMenu={toggleMenu}
        />

        {tab === "chat" && (
          <ErrorBoundary>
            <ChatView
              session={current}
              busy={busy}
              statusLine={statusLine}
              onSend={send}
              onStop={stop}
              onRegenerate={regenerate}
              activeModel={settings.activeModel}
              recallOn={memCfg.recall}
              onToggleRecall={() => onMemConfig("recall", memCfg.recall ? "off" : "on")}
              memItems={memItems}
              onMemAdd={addManual}
              onMemPin={(id, pinned) => memPin(id, pinned)}
              onMemDelete={(id) => memDelete(id)}
              onToast={showToast}
            />
          </ErrorBoundary>
        )}

        {tab === "memory" && (
          <div className="view-panel">
            <MemoryView
              items={memItems}
              stats={memStats}
              busy={memBusy}
              engineStatus={memEngine}
              onAdd={addManual}
              onOptimize={optimize}
              onClearAll={() => { memClear(); setMemEngine("engine idle"); }}
              onPin={(id, pinned) => memPin(id, pinned)}
              onDelete={(id) => memDelete(id)}
            />
          </div>
        )}

        {tab === "graph" && <GraphView onToast={showToast} />}

        {tab === "dashboard" && <DashboardView onToast={showToast} />}

        {tab === "profile" && <ProfileView onToast={showToast} />}

        {tab === "setup" && (
          <div className="view-panel">
            <SetupView
              settings={settings}
              memConfig={{ ...memCfg, __tick: memTick }}
              embedModels={embedModels}
              onSetting={onSetting}
              onMemConfig={onMemConfig}
            />
          </div>
        )}
      </main>
      <Toast toast={toast} />
    </div>
  );
}