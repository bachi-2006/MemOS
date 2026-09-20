export const uid = () =>
  Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

export const truncate = (s, n) => {
  if (typeof s !== "string") s = s != null ? String(s) : "";
  return s.length > n ? s.slice(0, Math.max(0, n - 1)) + "…" : s;
};

export const estTokens = (s) => {
  if (typeof s !== "string") s = s != null ? String(s) : "";
  return Math.max(1, Math.round(s.length / 4));
};

export const fmtBytes = (b) => {
  if (!b || typeof b !== "number" || isNaN(b)) return "";
  const mb = b / (1024 * 1024);
  if (mb >= 1024) return (mb / 1024).toFixed(1) + " GB";
  return Math.round(mb) + " MB";
};

export const fmtTime = (ts) => {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "";
    const p = (n) => String(n).padStart(2, "0");
    return p(d.getHours()) + ":" + p(d.getMinutes());
  } catch {
    return "";
  }
};

export const fmtMeta = (m) => {
  if (!m || typeof m !== "object") return "";
  const t = fmtTime(m.ts || m.createdAt);
  const metaStr = typeof m.meta === "string" ? m.meta : (m.meta ? String(m.meta) : "");
  return (t ? t + (metaStr ? " · " : "") : "") + metaStr;
};

export const EMBEDDING_HINT = /embed|bge|granite-embedding|mxbai|bge-m3/i;