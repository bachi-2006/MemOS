const API = "/api/ollama";

export async function ollamaApi(path, body) {
  const res = await fetch(API + path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

export async function ollamaTags() {
  const r = await ollamaApi("/tags");
  return r.models || [];
}

export async function ollamaPs() {
  const r = await ollamaApi("/ps");
  return r.models || [];
}

export async function ollamaEmbed(model, input) {
  const r = await ollamaApi("/embed", { model, input });
  const emb = r.embeddings && r.embeddings[0];
  if (!emb) throw new Error("no embedding returned");
  return emb;
}

export async function ollamaChatOnce(model, messages, options, opts = {}) {
  const { think = false } = opts;
  const r = await ollamaApi("/chat", { model, messages, stream: false, think, options });
  return (r.message && r.message.content) || "";
}

export async function ollamaChatStream(payload, signal, onChunk) {
  const res = await fetch(API + "/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (!line) continue;
      let chunk;
      try { chunk = JSON.parse(line); } catch { continue; }
      onChunk(chunk);
    }
  }
  return buffer;
}