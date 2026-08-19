# MemOS — Complete Technical Architecture

> **System Overview:** Local-first persistent memory lifecycle and context injection engine for Local LLMs.

---

## 🏛️ System Architecture Diagram

```mermaid
flowchart TD
    subgraph Clients["User & Client Interfaces"]
        UI["Next.js Web UI\n(Port 3000)"]
        BRIDGE["MemOS Windows Bridge\n(Port 11435)"]
        CLI["PowerShell CLI\nsave_memory.ps1"]
        EXT["Chrome Extension /\nTampermonkey Script"]
    end

    subgraph API["FastAPI Gateway & Proxy (:8000 / :11435)"]
        OLL_API["/api/v1/ollama (Status & Models)"]
        PROX_API["/v1/models & /v1/chat/completions (SSE)"]
        MEM_API["/api/v1/memory (Search & Lifecycle)"]
        PROF_API["/api/v1/profile (Preferences)"]
        HEALTH["/health & /health/* (Diagnostics)"]
    end

    subgraph Engines["Core Cognitive Engines"]
        CTX["Context Builder Engine\n(Top-K Semantic + Graph Triples + Profile)"]
        ANALYZER["Chat Analysis Engine\n(Entity & Fact Extractor)"]
        LIFECYCLE["Lifecycle & Compression Engine\n(Recency, Frequency, Forgetting)"]
        CONFLICT["Conflict Detection Engine\n(Contradiction Flagging)"]
    end

    subgraph Storage["Persistent Multi-Store"]
        PG[("PostgreSQL 15\nCanonical Metadata & Scoring")]
        QD[("Qdrant Vector DB\n768d Embeddings")]
        NEO[("Neo4j 5\nKnowledge Graph Triples")]
        RD[("Redis 7\nFast Session Cache")]
    end

    subgraph Inference["Local Inference"]
        OLLAMA["Ollama Local Server\n(Port 11434)"]
    end

    UI --> API
    BRIDGE --> API
    CLI --> API
    EXT --> API

    API --> CTX
    API --> ANALYZER
    API --> LIFECYCLE
    API --> CONFLICT

    CTX --> QD
    CTX --> NEO
    CTX --> PG

    ANALYZER --> PG
    ANALYZER --> QD
    ANALYZER --> NEO

    LIFECYCLE --> PG
    LIFECYCLE --> QD
    LIFECYCLE --> NEO

    CTX --> OLLAMA
    ANALYZER --> OLLAMA
```

---

## 📦 Multi-Store Roles & Division of Responsibilities

1. **PostgreSQL 15 (Canonical Relational Metadata)**:
   - Tables: `users`, `chats`, `messages`, `memories`, `user_profiles`, `analysis_history`.
   - Stores lifecycle mathematical scores (`importance_score`, `confidence_score`, `access_count`, `status`).

2. **Qdrant Vector DB (Semantic Vector Indexing)**:
   - Collection: `memory_vectors`.
   - Stores dense embeddings generated via local `nomic-embed-text` with cosine similarity filtering.

3. **Neo4j 5 (Associative Knowledge Graph)**:
   - Nodes: `User`, `Project`, `Technology`, `Skill`, `Concept`.
   - Edges: `[:DEVELOPING]`, `[:USES]`, `[:PREFERS]`, `[:SKILLED_IN]`.

4. **Redis 7 (Low-Latency Cache)**:
   - Used for quick session lookup, rate limiting, and temporary token streams.
