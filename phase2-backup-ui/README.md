# Phase 2 — Backup Build UI (standalone chat)

A clean, hand-crafted, framework-free chat UI that talks **directly to the locally
downloaded Ollama models** (`qwen3.5:9b`, `qwen3:latest`) over
`http://127.0.0.1:11434/api/chat`. It is a deliberate contrast to the main MemOS
workspace UI and is kept fully separate from it.

## Status

- **Marked:** Phase 2 / Backup Build.
- **Design goal:** non-generic, restrained, typographic UI (system fonts, a
  signature indigo→violet accent, soft depth, one subtle background glow, no
  emoji). Built by hand, not generated.
- **Currently:** advanced working build — streaming chat, **built-in adaptive
  client-side memory engine**, memory manager panel, settings.

## Isolation from the main MemOS project

This UI lives only in `phase2-backup-ui/` and is designed not to blend with the
main project:

| What | This UI | Main MemOS project |
| --- | --- | --- |
| Server | none — calls Ollama directly on `127.0.0.1:11434` | FastAPI backend on `:8000`, Next.js on `:3000` |
| Storage | chat = session-only (`sessionStorage`); **memories = local IndexedDB** (`memos-phase2`) | PostgreSQL/Qdrant/Neo4j/Redis |
| Model list | Ollama `/api/tags` + `/api/ps` (installed + loaded state) | same backend pool + extensions |
| App code | single `chat.html`, no build step, no deps | `backend/`, `frontend/`, `scripts/`, `docs/` |

It never imports, calls, or configures anything from `backend/`, `frontend/`,
`scripts/`, or `docs/`. Running it does not touch the MemOS databases or memory
store, and nothing here is written to the repo's tracked app tree beyond this
folder.

## Run (one click)

Double-click `start.bat`, or:

```powershell
python -m http.server 5150 --bind 127.0.0.1 --directory C:\Kaboom\Projects\MemOs\phase2-backup-ui
```

then open `http://127.0.0.1:5150/chat.html`. A plain `file://` open will not work
(Ollama rejects the `null` origin with 403); it must be served over HTTP on a
localhost origin.

## Features

### Chat
- **Multiple conversations**, session-local, with a sidebar switcher; the active
  one is remembered until the tab closes.
- **Streaming** via `fetch` + `ReadableStream` NDJSON parsing over `/api/chat`.
- **Thinking shown** — qwen3 reasoning tokens stream into a left-ruled, dim
  "thinking" block that auto-opens while thinking and collapses when done.
- **Regenerate** per reply (drops the trailing assistant turns and re-sends).
- **Copy** per message.
- **Context windowing** — only the last N messages are sent to the model.
- Cold-start counter (`loading model··· Ns`) while the weights load on CPU.

### Model manager (sidebar)
- Installed models from `/api/tags`: name, parameter size, quant, on-disk size.
- **Loaded state** from `/api/ps` (green dot + "loaded" badge, re-checked every
  15 s and after each reply).
- Embedding-only models (`nomic-embed-text`) greyed out and disabled.
- Switching the active model is instant — the request carries the chosen tag.

### Settings
- **Compute**: CPU (`num_gpu: 0`) or GPU. Defaults to CPU — on this machine the
  CUDA runtime crashes; `gpu` is an explicit opt-in.
- **Thinking**: toggle qwen3 deep-reasoning off/on. Defaults to **off** — on this
  Ollama build (`qwen3.5:9b`, v0.33.3) thinking burns the whole token budget and
  emits no visible reply; off yields reliable, fast output.
- **Temperature** slider (0–2), **max tokens** (`num_predict`), **context**
  (last-N messages), and a per-session **system prompt**.
- Light/dark theme toggle (persisted to `localStorage`).

### Memory engine (MemOS — built-in)
A full client-side adaptive memory pipeline, mirroring the MemOS backend
services but running entirely in the browser against Ollama:

- **Memory store** — persistent, per-browser IndexedDB (`memos-phase2`). Survives
  refresh; independent of chat sessions.
- **Auto-extraction** — after every completed reply the transcript is run through
  the local model to pull out a summary, facts, projects, technologies,
  preferences, goals, skills, and decisions (small talk is ignored).
- **Deduplication** — exact-content matches bump `access_count` + confidence
  instead of creating a duplicate.
- **Conflict detection** — new facts are checked against the last 12 active
  memories; contradictions are flagged and surfaced in the UI.
- **Importance scoring** — recency + frequency + entity count + confidence + pin
  bonus, re-computed on access.
- **Semantic recall** — before each prompt, the query is embedded with a local
  embedding model (`nomic-embed-text`) and the top-K memories are injected into
  the prompt context (cosine similarity, pinned memories boosted).
- **Lifecycle** — periodic sweep archives low-importance stale memories and
  forgets quiet archived ones; **Optimize** runs instant compression
  (LLM-synthesized "Compressed Archive" note) + adaptive forgetting.
- **Memory panel** — sidebar tab with stats, search, pin/delete, manual add, and
  importance/confidence bars; conflict warnings and status badges.

### Transfer & shortcuts
- **Export** the active conversation to a local `.json` file; **import** restores
  it (title, messages, reasoning) and, if valid, switches to the stored model.
- `Enter` send · `Shift+Enter` newline · `Esc` stop · `Alt+R` regenerate ·
  `Ctrl+N` new chat · `Ctrl+1..9` switch conversation · `Ctrl+Enter` send.

### Production-quality details
- Markdown renderer: fenced code blocks, inline code, headings, bold/italic,
  strikethrough, ordered/unordered lists, blockquotes, clickable links — no HTML
  injection (everything is escaped first). Rendered live while streaming.
- Message timestamps shown alongside each reply's token/time meta.
- Rough token counter per reply (`chars / 4`) + generation time.
- `aria-live` status line, `focus-visible` outlines, `prefers-reduced-motion`
  respected, responsive layout (< 860 px: slide-over sidebar + hamburger).
- A real inline error surfaces when Ollama is unreachable or a call fails.

## Development roadmap (remaining)

1. Persist conversations to an opt-in local file (never the backend stores).
2. Multi-model routing (embed locally, route to the best fit).
3. Per-model default settings saved alongside the conversation export.

> Conversation persistence still stays out of scope by design. **Memories**, by
> contrast, are now durable on purpose — they are the whole point of the memory
> engine and live in IndexedDB, never the MemOS backend stores.

## Notes

- Requires a running Ollama (`ollama serve`) with the downloaded models present.
- On this machine Qwen runs on CPU (CUDA driver issue); reply latency is a few
  seconds after load. Loading a 9B model takes several seconds the first time.