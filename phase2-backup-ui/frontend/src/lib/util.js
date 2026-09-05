export const uid = () =>
  Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

export const truncate = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

export const estTokens = (s) => Math.max(1, Math.round((s || "").length / 4));

export const fmtBytes = (b) => {
  if (!b) return "";
  const mb = b / (1024 * 1024);
  if (mb >= 1024) return (mb / 1024).toFixed(1) + " GB";
  return Math.round(mb) + " MB";
};

export const fmtTime = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  const p = (n) => String(n).padStart(2, "0");
  return p(d.getHours()) + ":" + p(d.getMinutes());
};

export const fmtMeta = (m) => {
  const t = fmtTime(m.ts || m.createdAt);
  return (t ? t + (m.meta ? " · " : "") : "") + (m.meta || "");
};

export const EMBEDDING_HINT = /embed|bge|granite-embedding|mxbai|bge-m3/i;