# Phase 2 — Full-Stack Build (React + FastAPI)

The Phase 2 chat interface, rebuilt as a real full-stack website:

- **FastAPI backend** (`backend/`) on port **5151** — a small proxy to the local
  Ollama server (`127.0.0.1:11434`) and the static host for the built frontend.
- **React frontend** (`frontend/`) — Vite + React 18 JSX build with live
  streaming chat, an adaptive **client-side memory engine**, memory manager,
  settings, import/export, light/dark theme, and full responsive layout.
- **Memory storage** stays **in the browser (IndexedDB, `memos-phase2`)** —
  nothing sensitive touches the MemOS backend stores.

## Run (one click)

1. Make sure Ollama is running with the models downloaded.
2. Build the frontend once:

```powershell
cd frontend
npm install     # first time only
npm run build
```

3. Double-click `start.bat` (or `python backend\run.py`) and open
   `http://127.0.0.1:5151`.

The backend serves the built `frontend/dist` and proxies `/api/ollama/*` to
Ollama. For development you can also run `npm run dev` (Vite on `:5173`,
`/api` proxied to `:5151`).

## Layout

| Path | Purpose |
| --- | --- |
| `backend/app/main.py` | FastAPI app: Ollama proxy (`/api/ollama/chat|embed|generate|tags|ps`), `/api/health`, SPA fallback |
| `backend/run.py` | uvicorn runner, port 5151 |
| `frontend/src/App.jsx` | app orchestrator: sessions, streaming, memory wiring, shortcuts |
| `frontend/src/components/` | Sidebar, Topbar, ChatView, MessageItem, Composer, MemoryView, SetupView, Toast |
| `frontend/src/lib/` | `ollama.js` (proxy calls), `memory.js` (memory engine), `markdown.js`, `config.js`, `util.js` |
| `frontend/src/hooks/useMemory.js` | React binding to the IndexedDB memory store |
| `phase2-backup-ui/chat.html` | legacy static build (kept as reference) |

## Features

### Chat
- Multiple conversations (session-local), Live streaming with qwen3 reasoning
  shown in a collapsible "thinking" block, Regenerate, Copy, context windowing,
  model loading state, timestamps + token/time meta.

### Memory engine
- IndexedDB store (`memos-phase2`), auto-extraction after each reply,
  deduplication, conflict detection, importance scoring, semantic recall
  (embeddings + cosine, pinned boost), lifecycle archiving/forgetting, manual
  add + Optimize compression.

### Setup
- Compute CPU/GPU, thinking on/off, temperature, max tokens, context window,
  system prompt, recall / auto-extract / embedding model / top-K / compress
  days. Theme persisted to `localStorage`.

## Requirements
- Python 3.10+ (`fastapi`, `uvicorn`, `httpx`), Node 18+ (`npm run build`).
- Ollama running locally with a chat model (e.g. `qwen3.5:9b`) and an embedding
  model (e.g. `nomic-embed-text`).

## Shortcuts
`Enter` send · `Shift+Enter` newline · `Esc` stop · `Alt+R` regenerate ·
`Ctrl+N` new chat · `Ctrl+1..9` switch · `Ctrl+Enter` send.