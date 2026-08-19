# MemOS: Adaptive Memory Lifecycle Management Framework

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.1.3-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC2626.svg?logo=qdrant&logoColor=white)](https://qdrant.tech)
[![Neo4j](https://img.shields.io/badge/Neo4j-Knowledge_Graph-008CC1.svg?logo=neo4j&logoColor=white)](https://neo4j.com)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-white.svg?logo=ollama&logoColor=black)](https://ollama.com)

**MemOS** is an autonomous, persistent long-term memory framework built for local Large Language Models (LLMs) and companion agent applications. It extends local LLMs (such as Ollama with Llama 3, Qwen, or Mistral) with multi-store memory indexing, automated conversation analysis, real-time knowledge graph extraction, semantic vector search, dynamic importance decay, adaptive compression, and conflict resolution.

---

## 🌟 Key Highlights & Capabilities

- **🧠 Multi-Store Memory Architecture**:
  - **Relational Metadata (PostgreSQL)**: Canonical storage for user profiles, conversation history, memory status, and scoring metrics.
  - **Vector Search (Qdrant)**: High-dimensional semantic vector indexing and similarity retrieval using local embeddings (`nomic-embed-text`).
  - **Knowledge Graph (Neo4j)**: Entity-relationship graph extraction and associative link exploration across conversations.
  - **Fast Cache (Redis)**: Low-latency caching for active sessions and lifecycle jobs.
- **⚡ Automated Chat Analysis & Memory Optimization**:
  - **🧠 Analyze Chat**: Parses conversation transcripts, ignores greetings and small talk, extracts structured facts/technologies/projects/skills, eliminates duplicates, and updates graph triples.
  - **🧹 Optimize Memory**: Sweeps the entire memory store, recalculates importance scores, triggers LLM compression on stale memories, and cleans up contradictory facts.
- **🎯 Dynamic Context Augmentation & Personalization**:
  - Automatically enriches prompts with relevant semantic memories, knowledge graph triples, user profile preferences, active projects, and pinned notes before calling Ollama.
- **⏳ Adaptive Memory Lifecycle Engine**:
  - **Importance Scoring**: Mathematical weighted decay ($Recency \times 0.3 + Frequency \times 0.3 + Entity \times 0.2 + Confidence \times 0.2 + Pin$).
  - **Memory Compression**: Synthesizes older memories into compact summaries via LLM.
  - **Unified Multi-Store Deletion**: Hard deletion synchronized across PostgreSQL, Qdrant, and Neo4j (no ghost memories).
- **🔌 1-Button Ollama Desktop & Proxy Bridge**:
  - **OpenAI Proxy (`/v1/chat/completions` & `/v1/models`)**: Drop-in OpenAI-compatible streaming proxy (SSE) on port `11435` / `8000`.
  - **Windows Bridge (`scripts/start_bridge.bat`)**: 1-click local connection detector and proxy launcher.
  - **PowerShell CLI (`scripts/save_memory.ps1`)**: Push memories directly from your shell.
  - **Browser Extension**: 1-click memory sharing from ChatGPT, Claude, or WebUIs.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Clients["User & Client Interfaces"]
        UI["Next.js Modern Web UI\n(Port 3000)"]
        EXT["Chrome Extension /\nTampermonkey Plugin"]
        CLI["PowerShell CLI\nsave_memory.ps1"]
        PROXY["Ollama Desktop /\nOpen WebUI Proxy"]
    end

    subgraph Backend["MemOS Backend (FastAPI - Port 8000)"]
        API["REST API & OpenAI Proxy"]
        ANALYZER["Chat Analysis Engine"]
        CTX_BUILDER["Context Builder Engine"]
        LIFECYCLE["Lifecycle & APScheduler Engine"]
        CONFLICT["Conflict Resolution Engine"]
    end

    subgraph Storage["Persistent Multi-Store & Local LLM"]
        PG[("PostgreSQL 15\nCanonical Metadata")]
        QD[("Qdrant Vector DB\nSemantic Embeddings")]
        NEO[("Neo4j 5\nKnowledge Graph")]
        RD[("Redis 7\nCache")]
        OLLAMA["Local Ollama Instance\n(Port 11434)"]
    end

    UI --> API
    EXT --> API
    CLI --> API
    PROXY --> API

    API --> CTX_BUILDER
    API --> ANALYZER
    API --> LIFECYCLE
    API --> CONFLICT

    ANALYZER --> OLLAMA
    CTX_BUILDER --> OLLAMA
    LIFECYCLE --> OLLAMA

    ANALYZER --> PG
    ANALYZER --> QD
    ANALYZER --> NEO

    CTX_BUILDER --> QD
    CTX_BUILDER --> NEO
    CTX_BUILDER --> PG

    LIFECYCLE --> PG
    LIFECYCLE --> QD
```

---

## 📂 Project Structure

```
MemOs/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint & lifespan scheduler
│   │   ├── api/                        # API route controllers
│   │   │   ├── auth.py                 # JWT User authentication & registration
│   │   │   ├── chats.py                # Chat session storage and message history
│   │   │   ├── dashboard.py            # Real-time metrics & memory distribution
│   │   │   ├── deps.py                 # Security dependencies & companion fallbacks
│   │   │   ├── graph.py                # Knowledge graph retrieval endpoints
│   │   │   ├── memory.py               # Memory storage, search, and chat analysis
│   │   │   ├── ollama.py               # Ollama model listing, chat & share-memory hook
│   │   │   ├── profile.py              # User profile & preferences
│   │   │   └── proxy.py                # OpenAI-compatible proxy (/v1/chat/completions)
│   │   ├── core/                       # Core configuration & JWT security
│   │   ├── database/                   # SQLAlchemy engine & SQLite fallback session
│   │   ├── models/                     # Database models (User, Memory, Chat, Profile, etc.)
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── services/                   # Business logic & external service connectors
│   │   │   ├── analysis_service.py     # Conversation parsing & entity extraction
│   │   │   ├── conflict_service.py     # Contradiction detection engine
│   │   │   ├── context_builder.py      # Personalized prompt context assembly
│   │   │   ├── graph_service.py        # Neo4j Cypher query manager
│   │   │   ├── importance_service.py   # Memory importance scoring formula
│   │   │   ├── lifecycle_service.py    # Compression & forgetting engines
│   │   │   ├── memory_service.py       # Dual-storage (Postgres + Qdrant) indexing
│   │   │   ├── ollama_service.py       # Ollama chat & embedding client
│   │   │   └── qdrant_service.py       # Qdrant collection & search manager
│   │   └── workers/
│   │       └── scheduler.py            # APScheduler nightly memory maintenance jobs
│   └── tests/                          # Pytest unit & integration test suite
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── app/                        # Next.js 14 App router
│       │   ├── globals.css             # Theme styles & scrollbar setup
│       │   ├── layout.tsx              # Root HTML wrapper
│       │   └── page.tsx                # Main workspace container
│       └── components/                 # UI Tabs & Modals
│           ├── AnalysisModal.tsx       # Multi-step animated chat analysis modal
│           ├── ChatTab.tsx             # Interactive chat with personalization toggle
│           ├── DashboardTab.tsx        # Memory distribution & metrics cards
│           ├── GraphTab.tsx            # Neo4j entity & knowledge triple explorer
│           ├── SearchTab.tsx           # Semantic vector search & memory table
│           ├── Sidebar.tsx             # Navigation sidebar
│           ├── UserProfileTab.tsx      # Auto-learned profile editor
│           └── types.ts                # TypeScript data interfaces
├── scripts/
│   ├── extension/                      # Chrome Extension (Manifest V3)
│   │   ├── manifest.json
│   │   └── content.js
│   ├── memos_browser_plugin.user.js    # Tampermonkey / Greasemonkey userscript
│   └── save_memory.ps1                 # PowerShell CLI helper script
├── docker-compose.yml                  # Multi-container orchestration
└── README.md                           # Master project documentation
```

---

## 🚀 Quickstart Guide

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) installed.
- [Ollama](https://ollama.com/) running locally with your desired models installed:
  ```bash
  ollama pull qwen3.5:9b
  ollama pull nomic-embed-text
  ```

### 1. Launch with Docker Compose (Recommended)

Start all services (Postgres, Redis, Qdrant, Neo4j, FastAPI backend, Next.js frontend) with a single command:

```bash
# Navigate to project root
cd MemOs

# Start all microservices in the background
docker compose up -d --build
```

#### Services Access Endpoints:
| Service | URL | Description |
| :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost:3000](http://localhost:3000) | Full Next.js 14 Web Workspace |
| **FastAPI Backend & Swagger** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive OpenAPI Documentation |
| **Qdrant Vector Dashboard** | [http://localhost:6333/dashboard](http://localhost:6333/dashboard) | Vector Collection Explorer |
| **Neo4j Browser** | [http://localhost:7474](http://localhost:7474) | Graph Database Visualizer |

---

### 2. Standalone Local Development (Without Docker)

You can also run MemOS directly on your local machine:

#### Backend Setup:
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # On Windows (or source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt

# Run FastAPI dev server (defaults to local SQLite companion mode if Postgres is absent)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📡 API Reference Overview

The FastAPI backend exposes RESTful endpoints at `/api/v1`:

### 1. Chat & Personalization
- `POST /api/v1/ollama/chat`: Send a prompt with optional context personalization toggle (`personalized: true/false`).
- `GET /api/v1/ollama/models`: List models available in the local Ollama instance.
- `POST /api/v1/chats/send`: Send and store messages in a persistent chat session with automatic context injection.
- `GET /api/v1/chats/`: List conversation sessions for the active user.
- `GET /api/v1/chats/{chat_id}/messages`: Retrieve message history for a specific chat.

### 2. Memory Extraction & Semantic Search
- `POST /api/v1/memory/analyze-chat`: Run the multi-step chat analysis engine to extract facts, entities, projects, technologies, and generate vector embeddings & graph triples.
- `GET /api/v1/memory/search?query=...&limit=5`: High-dimensional cosine similarity search across Qdrant vector memory.
- `POST /api/v1/memory/store`: Explicitly create and index a canonical memory into PostgreSQL and Qdrant.
- `GET /api/v1/memory/all`: Fetch all active relational memories for the current user.

### 3. Knowledge Graph & Profile
- `GET /api/v1/graph/`: Retrieve Neo4j nodes and knowledge triples scoped to the current user.
- `GET /api/v1/profile/`: Get auto-learned user profile (languages, frameworks, projects, skills, style, learning goals).
- `PATCH /api/v1/profile/`: Manually update profile preferences.

### 4. Metrics & Analytics
- `GET /api/v1/dashboard/metrics`: Real-time lifecycle statistics (active, archived, forgotten memories, importance scores, compression ratios).

### 5. OpenAI / Ollama Proxy Compatibility
- `POST /v1/chat/completions` or `POST /api/chat`: Universal proxy endpoint. Route standard OpenAI/Ollama client requests to MemOS to automatically inject long-term vector memory before dispatching to Ollama.

---

## 🛠️ Client & Extension Integrations

### 1. PowerShell Terminal CLI
Push any snippet or thought directly into MemOS from the command line:
```powershell
.\scripts\save_memory.ps1 -Content "MemOS stores vectors in Qdrant and knowledge triples in Neo4j." -Source "terminal"
```

### 2. Browser Extension (Chrome / Edge / Brave)
1. Open your browser extension settings (`chrome://extensions/`).
2. Enable **Developer mode** (top right).
3. Click **Load unpacked** and select the `scripts/extension` folder.
4. Highlight any text on any webpage (ChatGPT, Claude, documentation) and click the **🧠 Save to MemOS** button.

### 3. Tampermonkey / Greasemonkey Userscript
Install `scripts/memos_browser_plugin.user.js` in Tampermonkey or Violentmonkey to inject a floating **🧠 Share with MemOS** button on any webpage.

---

## 🧪 Testing

Run the automated test suite with `pytest`:

```bash
# Run all backend unit and integration tests
pytest backend/tests
```

All 7 test suites validate:
- Chat analysis JSON extraction and parsing fallbacks.
- Memory deduplication and importance scoring.
- Personalized context assembly (vector + graph + profile).
- User profile continuous auto-updating.
- Multi-store pipeline execution with mock drivers.

---

## 📄 License & Contributing

MemOS is open-source software licensed under the MIT License. Contributions, feedback, and feature suggestions are welcome!
