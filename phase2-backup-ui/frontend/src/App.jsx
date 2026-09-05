import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import ChatView from "./components/ChatView.jsx";
import Toast from "./components/Toast.jsx";
import { useMemory } from "./hooks/useMemory.js";
import { loadSettings, saveSettings, memCfg, THEME_KEY } from "./lib/config.js";
import { ollamaTags, ollamaPs, ollamaChatStream } from "./lib/ollama.js";
import {
  memRecall,
  memExtractFromChat,
  memOptimizeNow,
  memAddManual,
  memDelete,
  memClear,
  memPin,
  memLifecycle,
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
  const showToast = (html) => {
    setToast({ html, key: uid() });
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
      sessions: [{ id, title: "", messages: [] }, ...s.sessions],
      currentId: id,
    }));
  };
  const selectSession = (id) => {
    setSettings((s) => ({ ...s, currentId: id }));
  };
  const deleteSession = (id) => {
    setSettings((s) => {
      const sessions = s.sessions.filter((x) => x.id !== id);
      const currentId = s.currentId === id ? (sessions[0] ? sessions[0].id : null) : s.currentId;
      return { ...s, sessions, currentId };
    });
  };

  const pushMsg = (sid, msg) => {
    setSettings((s) => ({
      ...s,
      sessions: s.sessions.map((sess) =>
        sess.id === sid ? { ...sess, messages: [...(sess.messages || []), msg] } : sess
      ),
    }));
  };
  const patchSession = (sid, fn) => {
    setSettings((s) => ({
      ...s,
      sessions: s.sessions.map((sess) => (sess.id === sid ? fn(sess) : sess)),
    }));
  };
  const patchMessage = (sid, mid, fn) => {
    setSettings((s) => ({
      ...s,
      sessions: s.sessions.map((sess) =>
        sess.id === sid
          ? { ...sess, messages: (sess.messages || []).map((m) => (m.id === mid ? fn(m) : m)) }
          : sess
      ),
    }));
  };
  const ensureTitle = (sid, text) => {
    const sess = settingsRef.current.sessions.find((x) => x.id === sid);
    if (sess && !sess.title && text) {
      patchSession(sid, (ss) => ({ ...ss, title: truncate(text, 34) }));
    }
  };

  /* ---------- payload ---------- */
  const buildPayload = (sess, lastUserText) => {
    const s = settingsRef.current;
    if (!s.activeModel) return null;
    let out = (sess.messages || [])
      .filter((m) => !m.streaming)
      .map((m) => ({ role: m.role, content: m.content }));
    if (lastUserText != null) {
      if (out.length && out[out.length - 1].role === "user") out[out.length - 1].content = lastUserText;
      else out.push({ role: "user", content: lastUserText });
    }
    const n = Math.max(1, Number(s.windowN) || 12);
    out = out.slice(-n);
    return {
      model: s.activeModel,
      messages: out,
      stream: true,
      ...(s.thinking ? {} : { think: false }),
      options: {
        temperature: Number(s.temp) || 0.7,
        num_predict: Number(s.numPredict) || 512,
        ...(s.compute !== "gpu" ? { num_gpu: 0 } : {}),
      },
    };
  };

  /* ---------- streaming ---------- */
  const streamTurn = async (sess, augmented) => {
    const payload = buildPayload(sess, augmented == null ? null : augmented);
    if (!payload) {
      pushStatus("select a model first", "#ef4444", 2800);
      return;
    }
    const sid = sess.id;
    const mid = uid();
    const acc = { text: "", reasoning: "", firstTok: false };
    pushMsg(sid, { id: mid, role: "assistant", content: "", reasoning: "", meta: payload.model, ts: Date.now(), streaming: true });
    setBusy(true);
    setMemEngine(payload.model + " · streaming");

    const ctrl = new AbortController();
    streamRef.current = { ctrl, sid, mid, acc };
    let aborted = false;

    let tick = setInterval(() => {
      if (acc.firstTok) return;
      const ticks = ((Date.now() / 500) | 0) % 3 + 1;
      patchMessage(sid, mid, (m) => ({ ...m, content: "…" + ".".repeat(ticks), streaming: true }));
    }, 600);

    let flushTimer = null;
    const flush = () => {
      if (flushTimer) return;
      flushTimer = setTimeout(() => {
        flushTimer = null;
        patchMessage(sid, mid, (m) => ({ ...m, content: acc.text, reasoning: acc.reasoning }));
      }, 80);
    };

    try {
      await ollamaChatStream(payload, ctrl.signal, (chunk) => {
        clearInterval(tick);
        acc.firstTok = true;
        if (chunk.message && typeof chunk.message.content === "string") acc.text += chunk.message.content;
        if (chunk.message && typeof chunk.message.reasoning_content === "string") acc.reasoning += chunk.message.reasoning_content;
        flush();
      });
      clearInterval(tick);
      clearTimeout(flushTimer);
      patchMessage(sid, mid, (m) => ({
        ...m,
        content: acc.text,
        reasoning: acc.reasoning,
        streaming: false,
      }));
    } catch (err) {
      clearInterval(tick);
      clearTimeout(flushTimer);
      if (err && err.name === "AbortError") {
        aborted = true;
        patchMessage(sid, mid, (m) => ({ ...m, content: acc.text, reasoning: acc.reasoning, streaming: false }));
      } else {
        patchMessage(sid, mid, (m) => ({
          ...m,
          content: acc.text || "⚠ Something went wrong — is Ollama running?",
          reasoning: acc.reasoning,
          streaming: false,
          meta: (m.meta || "") + " · error",
        }));
      }
    } finally {
      setBusy(false);
      streamRef.current = null;
    }

    if (!aborted) {
      const usr = (sess.messages || []).find((m) => m.role === "user");
      if (usr) ensureTitle(sid, usr.content);
      memLifecycle();
      if (memCfg.autoExtract) {
        setMemBusy("Extracting…");
        const final = settingsRef.current.sessions.find((x) => x.id === sid);
        try {
          const r = await memExtractFromChat(final?.messages || [], ctx);
          if (r && r.created) {
            setMemEngine(r.created + " new · " + r.total + " total");
            pushStatus("memory · " + r.created + " new", "#a78bfa", 3600);
          } else if (r) {
            setMemEngine(r.total + " memories");
            pushStatus("memory · no new facts", "#00c896", 2400);
          }
        } catch (e) {
          console.error("extract failed", e);
        }
        setMemBusy("");
      }
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
      setSettings((s) => ({
        ...s,
        sessions: [{ id, title: "", messages: [] }, ...s.sessions],
        currentId: id,
      }));
      sid = id;
      sess = { id, title: "", messages: [] };
    }
    const userMsg = { id: uid(), role: "user", content: text, ts: Date.now() };
    pushMsg(sid, userMsg);
    ensureTitle(sid, text);
    setStatusLine([]);

    const sessWithUser = { ...sess, messages: [...(sess.messages || []), userMsg] };

    if (!settingsRef.current.activeModel) {
      const name = await autoPickModel();
      if (name) {
        settingsRef.current = { ...settingsRef.current, activeModel: name };
        setSettings((s) => ({ ...s, activeModel: name }));
      }
    }

    let augmented = null;
    if (memCfg.recall) {
      try {
        const rc = await memRecall(text, ctx);
        if (rc.memories && rc.memories.length) {
          augmented = rc.prompt;
          pushStatus("memories recalled · " + rc.memories.length, "#00c896", 2600);
        }
      } catch {}
    }
    await streamTurn(sessWithUser, augmented || null);
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
    for (let i = msgs.length - 1; i >= 0; i--) if (msgs[i].role === "user") { lastUser = i; break; }
    if (lastUser < 0) return;
    const truncated = msgs.slice(0, lastUser + 1);
    patchSession(sid, (ss) => ({ ...ss, messages: truncated }));
    await streamTurn({ ...sess, messages: truncated }, null);
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
      showToast("Imported <b>" + clean.length + "</b> conversation" + (clean.length > 1 ? "s" : "") + ".");
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
      if (!settingsRef.current.currentId) newChat();
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
          title={current ? current.title || "New conversation" : "New conversation"}
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
        <ChatView
          session={current}
          busy={busy}
          statusLine={statusLine}
          onSend={send}
          onStop={stop}
          onRegenerate={regenerate}
        />
      </main>
      <Toast toast={toast} />
    </div>
  );
}