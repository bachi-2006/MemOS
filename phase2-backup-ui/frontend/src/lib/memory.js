import { uid } from "./util.js";
import { memCfg, EMBED_DEFAULT } from "./config.js";
import { ollamaChatOnce, ollamaEmbed } from "./ollama.js";

const DB_NAME = "memos-phase2";
const DB_VER = 1;
const DAY = 86400000;

let memDB = null;
let memCache = null;
const listeners = new Set();

function openMemDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains("memories")) {
        const store = db.createObjectStore("memories", { keyPath: "id" });
        store.createIndex("by_importance", "importance_score");
        store.createIndex("by_status", "status");
        store.createIndex("by_created", "createdAt");
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function txStore(mode) {
  return memDB.transaction("memories", mode).objectStore("memories");
}

function idbReq(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function emit() {
  listeners.forEach((f) => {
    try { f(); } catch {}
  });
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function memSnapshot() {
  return memCache ? memCache.slice() : [];
}

export async function memInit() {
  try {
    memDB = await openMemDB();
    memCache = await idbReq(txStore("readonly").getAll());
    if (!memCache) memCache = [];
  } catch (e) {
    memDB = null;
    memCache = [];
    console.error("MemOS memory store unavailable:", e);
  }
  emit();
}

function memSave(m) {
  if (!memCache) memCache = [];
  memCache = memCache.filter((x) => x.id !== m.id);
  memCache.push(m);
  try { txStore("readwrite").put(m); } catch {}
  emit();
}

export function memDelete(id) {
  memCache = memCache.filter((x) => x.id !== id);
  try { txStore("readwrite").delete(id); } catch {}
  emit();
}

export function memPin(id, pinned) {
  const m = (memCache || []).find((x) => x.id === id);
  if (!m) return;
  m.pinned = !!pinned;
  m.importance_score = calcImportance(m, Date.now());
  memSave(m);
}

export function memClear() {
  memCache = [];
  if (memDB) {
    try { txStore("readwrite").clear(); } catch {}
  }
  emit();
}

function memVector(m) {
  if (m && Array.isArray(m.embedding) && m.embedding.length) return m.embedding;
  return null;
}

export function cosineSim(a, b) {
  if (!a || !b || a.length !== b.length) return 0;
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  if (na === 0 || nb === 0) return 0;
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

async function memEmbed(m) {
  if (memVector(m)) return m.embedding;
  try {
    m.embedding = await ollamaEmbed(memCfg.embedModel, m.content);
    memSave(m);
    return m.embedding;
  } catch {
    return null;
  }
}

export function calcImportance(m, now) {
  const createdAt = m.createdAt != null ? m.createdAt : Date.now();
  const daysOld = Math.max(0, (now - createdAt) / DAY);
  const recency = Math.max(0.1, 1.0 - daysOld * 0.05);
  const frequency = Math.min(2.0, 1.0 + (m.accessCount || 0) * 0.1);
  const entities = Math.min(1.5, 1.0 + (m.entities || []).length * 0.1);
  const confidence = m.confidence != null ? m.confidence : 1.0;
  const pin = m.pinned ? 2.0 : 0.0;
  return Math.round(((recency * 0.3) + (frequency * 0.3) + (entities * 0.2) + (confidence * 0.2) + pin) * 1000) / 1000;
}

export function memAddRaw(content, opts) {
  opts = opts || {};
  const now = Date.now();
  const m = {
    id: uid(),
    content,
    tags: opts.tags || [],
    entities: opts.entities || [],
    source: opts.source || "manual",
    status: "active",
    importance_score: opts.importance_score != null ? opts.importance_score : 1.0,
    confidence: opts.confidence != null ? opts.confidence : 1.0,
    accessCount: 0,
    pinned: !!opts.pinned,
    conflict: !!opts.conflict,
    conflictInfo: opts.conflictInfo || "",
    project: opts.project || "",
    collection: opts.collection || "",
    createdAt: now,
    updatedAt: now,
  };
  memSave(m);
  return m;
}

export async function memAddManual(content) {
  if (!content || !content.trim()) return null;
  const m = memAddRaw(content.trim(), {});
  await memEmbed(m);
  return m;
}

function memDedupe(existing, contentStr) {
  const key = contentStr.toLowerCase().trim();
  const hit = existing.find((m) => (m.content || "").toLowerCase().trim() === key);
  if (hit) {
    hit.accessCount = (hit.accessCount || 0) + 1;
    hit.confidence = Math.min(1.0, (hit.confidence != null ? hit.confidence : 0.8) + 0.05);
    hit.importance_score = calcImportance(hit, Date.now());
    hit.updatedAt = Date.now();
    memSave(hit);
    return hit;
  }
  return null;
}

async function memConflictCheck(newContent, ctx) {
  if (!memCfg.conflictCheck) return { detected: false, info: "" };
  const existing = (memCache || [])
    .filter((m) => m.status === "active" && m.conflict !== true)
    .slice(-12);
  if (!existing.length) return { detected: false, info: "" };
  const existingTexts = existing.map((m) => "- " + m.content).join("\n");
  const prompt =
    "Given the existing user memories:\n" + existingTexts +
    '\n\nNew statement: "' + newContent + '"\n\n' +
    "Does the new statement contradict any existing memory?\n" +
    "If YES, respond: CONFLICT: <memory id unused> | Explanation: <reason>\nIf NO, respond: NO CONFLICT";
  try {
    const response = await ollamaChatOnce(modelFor(ctx), [
      { role: "user", content: prompt },
    ], { temperature: 0.1, num_predict: 120, ...gpuOpts(ctx) }, { think: false });
    if (/CONFLICT\s*:/i.test(response || "")) {
      const expl = response.replace(/CONFLICT[\s\S]*?\|\s*/i, "").trim();
      return { detected: true, info: expl || response };
    }
  } catch {}
  return { detected: false, info: "" };
}

function modelFor(ctx) {
  return memCfg.extractModel || (ctx && ctx.activeModel) || "";
}

function gpuOpts(ctx) {
  return (ctx && ctx.compute !== "gpu") ? { num_gpu: 0 } : {};
}

function parseMemJSON(text) {
  try { return JSON.parse(text); } catch {}
  const m = text.match(/\{[\s\S]*\}/);
  if (m) { try { return JSON.parse(m[0]); } catch {} }
  return null;
}

export async function memExtractFromChat(messages, ctx) {
  if (!memCfg.autoExtract) return null;
  const chatMsgs = (messages || [])
    .filter((m) => !m.streaming && m.content && !/^\s*\[/.test(m.content))
    .slice(-8);
  if (!chatMsgs.length) return null;
  const transcript = chatMsgs
    .map((m) => (m.role === "user" ? "User: " : "Assistant: ") + m.content)
    .join("\n");

  const prompt =
    "You are an expert AI Memory Extraction System. Read the conversation transcript below.\n\n" +
    "CONVERSATION TRANSCRIPT:\n" + transcript + "\n\n" +
    "CRITICAL INSTRUCTIONS:\n" +
    '- IGNORE all greetings, pleasantries, small talk, and chit-chat (e.g., "hi", "hello", "how are you", "thanks", "bye").\n' +
    "- EXTRACT only meaningful knowledge, facts, user details, projects, technologies, decisions, preferences, goals, and skills.\n" +
    "- Output ONLY a valid JSON object (no commentary) with this exact shape:\n" +
    '{ "summary": "concise 1-2 sentence memory summary", "facts": ["fact 1", "fact 2"], "projects": ["Project"], "technologies": ["Tech"], "user_preferences": ["preference"], "goals": ["goal"], "skills": ["skill"], "important_decisions": ["decision"] }\n' +
    'If there is nothing meaningful to remember, return { "summary": "", "facts": [], "projects": [], "technologies": [], "user_preferences": [], "goals": [], "skills": [], "important_decisions": [] }';

  let llmText;
  try {
    llmText = await ollamaChatOnce(modelFor(ctx), [{ role: "user", content: prompt }], {
      temperature: 0.2, num_predict: 400, ...gpuOpts(ctx),
    }, { think: false });
  } catch (e) {
    return null;
  }
  const data = parseMemJSON(llmText);
  if (!data) return null;

  const existing = (memCache || []).slice();
  let createdCount = 0, dupCount = 0, conflictCount = 0;
  const createdIds = [];

  async function ingest(content, tags, collection, source) {
    if (!content || content.trim().length < 6) return false;
    const packed = content.trim().replace(/^(summary|decision|preference|goal):\s*/i, "");
    const prefix = { decision: "Decision: ", preference: "Preference: ", goal: "Goal: " }[tags[0]] || "";
    const final = prefix + packed;
    if (memDedupe(existing, final)) { dupCount++; return false; }
    const mm = memAddRaw(final, { tags, collection, source });
    createdIds.push(mm.id);
    createdCount++;
    return true;
  }

  if (data.summary && data.summary.trim().length > 10) {
    if (memDedupe(existing, data.summary.trim())) dupCount++;
    else {
      const mm = memAddRaw(data.summary.trim(), { tags: ["summary"], collection: "Summary", source: "chat_analysis" });
      createdIds.push(mm.id);
      createdCount++;
    }
  }
  for (const f of data.facts || []) await ingest(f, ["fact"], "Facts", "chat_analysis");
  for (const p of data.projects || []) await ingest(p, ["project"], "Projects", "chat_analysis");
  for (const t of data.technologies || []) await ingest(t, ["tech"], "Coding", "chat_analysis");
  for (const p of data.user_preferences || []) await ingest(p, ["preference"], "Personal", "chat_analysis");
  for (const g of data.goals || []) await ingest(g, ["goal"], "Personal", "chat_analysis");
  for (const sk of data.skills || []) await ingest(sk, ["skill"], "Personal", "chat_analysis");
  for (const d of data.important_decisions || []) await ingest(d, ["decision"], "Coding", "chat_analysis");

  for (const id of createdIds) {
    const m = (memCache || []).find((x) => x.id === id);
    if (!m) continue;
    await memEmbed(m);
    const c = await memConflictCheck(m.content, ctx);
    if (c.detected) { m.conflict = true; m.conflictInfo = c.info; memSave(m); conflictCount++; }
    m.importance_score = calcImportance(m, Date.now());
    memSave(m);
  }
  return { created: createdCount, duplicates: dupCount, conflicts: conflictCount, total: (memCache || []).length };
}

export async function memRecall(promptText, ctx) {
  if (!memCfg.recall) return { prompt: promptText, memories: [] };
  const all = (memCache || []).filter((m) => m.status === "active");
  if (!all.length) return { prompt: promptText, memories: [] };
  let qv;
  try { qv = await ollamaEmbed(memCfg.embedModel, promptText); } catch { return { prompt: promptText, memories: [] }; }
  const scored = [];
  for (const m of all) {
    const mv = memVector(m) || (await memEmbed(m));
    const score = mv ? cosineSim(qv, mv) : 0;
    if (score >= memCfg.recallThreshold) scored.push({ m, score: score + (m.pinned ? 0.15 : 0) });
  }
  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, memCfg.topK);
  if (!top.length) return { prompt: promptText, memories: [] };

  top.forEach(({ m }) => {
    m.accessCount = (m.accessCount || 0) + 1;
    m.importance_score = calcImportance(m, Date.now());
    memSave(m);
  });

  const lines = top.map(({ m, score }) => "• " + m.content + " (relevance " + score.toFixed(2) + ")").join("\n");
  const context =
    "=== RELEVANT LONG-TERM MEMORIES ===\n" + lines +
    "\n\nInstructions: Personalize your response using these relevant memories where appropriate.";
  return { prompt: context + "\n\nUser Question: " + promptText, memories: top.map((t) => ({ content: t.m.content, score: t.score })) };
}

export function memLifecycle() {
  const now = Date.now();
  const all = memCache || [];
  all.forEach((m) => {
    if (m.status === "active" && !m.pinned && m.importance_score < 0.3 && (now - m.createdAt) > 7 * DAY) {
      m.status = "archived"; memSave(m);
    }
  });
  all.forEach((m) => {
    if (m.status === "archived" && m.importance_score < 0.25 && (now - (m.updatedAt || m.createdAt)) > 14 * DAY) {
      m.status = "forgotten"; memSave(m);
    }
  });
  emit();
}

export async function memOptimizeNow(ctx) {
  const active = (memCache || []).filter((m) => m.status === "active");
  const cutoff = Date.now() - memCfg.compressDays * DAY;
  const olds = active.filter((m) => m.createdAt < cutoff && !m.pinned);
  let archivedCount = 0, forgottenCount = 0;

  if (olds.length >= 2) {
    const texts = olds.map((m) => "- " + m.content).join("\n");
    const prompt = "Compress the following older memories into a single concise, high-density long-term summary (2-3 sentences):\n\nMEMORIES:\n" + texts;
    try {
      const note = await ollamaChatOnce(modelFor(ctx), [{ role: "user", content: prompt }], {
        temperature: 0.3, num_predict: 200, ...gpuOpts(ctx),
      }, { think: false });
      if (note && note.trim().length > 10) {
        const m = memAddRaw("Compressed Archive: " + note.trim(), {
          tags: ["compressed_archive", "summary"], source: "lifecycle_compression", importance_score: 1.2,
        });
        await memEmbed(m);
      }
    } catch {}
    olds.forEach((m) => { m.status = "archived"; memSave(m); archivedCount++; });
  }

  (memCache || []).forEach((m) => {
    if (m.status === "archived" && m.importance_score < 0.25 && (Date.now() - (m.updatedAt || m.createdAt)) > 14 * DAY) {
      m.status = "forgotten"; memSave(m); forgottenCount++;
    }
  });
  return { archived: archivedCount, forgotten: forgottenCount };
}

export function memStats() {
  const all = memCache || [];
  return {
    total: all.length,
    active: all.filter((m) => m.status === "active").length,
    pinned: all.filter((m) => m.pinned).length,
    conflict: all.filter((m) => m.conflict).length,
    engine: all.length ? all.length + " memories" : "engine idle",
  };
}