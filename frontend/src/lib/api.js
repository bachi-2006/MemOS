// Unified Backend API Client for MemOS Single Source of Truth
const BASE = "/api/v1";

export function getAuthToken() {
  return localStorage.getItem("memos_auth_token") || "";
}

export function setAuthToken(token) {
  if (token) localStorage.setItem("memos_auth_token", token);
  else localStorage.removeItem("memos_auth_token");
}

function authHeaders() {
  const token = getAuthToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// -----------------------------------------------------------------------------
// Chats API
// -----------------------------------------------------------------------------

export async function fetchChats() {
  const res = await fetch(`${BASE}/chats/`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchChatMessages(chatId) {
  const res = await fetch(`${BASE}/chats/${chatId}/messages`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`${BASE}/chats/${chatId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function renameChat(chatId, title) {
  const res = await fetch(`${BASE}/chats/${chatId}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function streamChat({
  chatId,
  prompt,
  model,
  personalized = true,
  signal,
  onContext,
  onToken,
  onDone,
  onError,
}) {
  try {
    const res = await fetch(`${BASE}/chats/stream`, {
      method: "POST",
      headers: { ...authHeaders(), Accept: "text/event-stream" },
      body: JSON.stringify({
        chat_id: chatId || undefined,
        prompt,
        model: model || undefined,
        personalized,
      }),
      signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`HTTP ${res.status}: Failed to initiate stream`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawChunk = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);

        if (!rawChunk.startsWith("data: ")) continue;
        const dataStr = rawChunk.slice(6).trim();
        if (!dataStr) continue;

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.type === "context" && onContext) {
            onContext(parsed);
          } else if (parsed.token && onToken) {
            onToken(parsed.token, parsed.chat_id);
          } else if (parsed.done && onDone) {
            onDone(parsed);
          }
        } catch {
          // ignore single chunk parse errors
        }
      }
    }
  } catch (err) {
    if (onError) onError(err);
    else throw err;
  }
}

// -----------------------------------------------------------------------------
// Memories API
// -----------------------------------------------------------------------------

export async function fetchMemories({ status, collection, limit = 100, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (collection) params.append("collection", collection);
  if (limit) params.append("limit", limit);
  if (offset) params.append("offset", offset);

  const res = await fetch(`${BASE}/memory/all?${params.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : data.memories || [];
}

export async function createMemory({ content, tags = [], source = "manual", collection = "General" }) {
  const res = await fetch(`${BASE}/memory/store`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      content,
      tags: Array.isArray(tags) ? tags : [tags],
      source,
      collection,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteMemory(memoryId) {
  const res = await fetch(`${BASE}/memory/${memoryId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function pinMemory(memoryId, isPinned) {
  const res = await fetch(`${BASE}/memory/${memoryId}/pin?is_pinned=${isPinned}`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerOptimization() {
  const res = await fetch(`${BASE}/memory/optimize`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// -----------------------------------------------------------------------------
// Profile, Graph, Dashboard API
// -----------------------------------------------------------------------------

export async function fetchProfile() {
  const res = await fetch(`${BASE}/profile/`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function updateProfile(data) {
  const res = await fetch(`${BASE}/profile/`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchGraph() {
  const res = await fetch(`${BASE}/graph/`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchDashboardMetrics() {
  const res = await fetch(`${BASE}/dashboard/metrics`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
