# MemOS — Security, Privacy & Isolation Model

> **Local-First Security Policy:** Ensuring on-device privacy, session isolation, and secure local development.

---

## 🔒 Security Principles

### 1. User & Session Isolation (No Hardcoded Fallbacks)
- Resolved the historical `db.query(User).first()` pattern.
- Authenticated proxy requests resolve identity from the JWT subject; client-provided `user` and `x-user-id` values are only accepted when they match that subject.
- Anonymous companion access is restricted using the socket peer address. `X-Forwarded-For` is not trusted for this access-control decision.
- Prevents cross-contamination of memory spaces across different local sessions or user profiles.

### 2. Zero Unnecessary Cloud Exfiltration
- All embedding generation (`nomic-embed-text`) and inference (`qwen3.5:9b`, `llama3`, `mistral`) are executed via the local Ollama instance (`127.0.0.1:11434`).
- No conversation transcripts, memory vectors, or graph triples are dispatched to third-party cloud APIs.

### 3. Unified Deletion & Memory Sanitation
- Deletion is cross-synchronized across PostgreSQL, Qdrant, and Neo4j.
- Eliminates "ghost memories" where a deleted record in relational storage remains discoverable via vector or graph queries.
- Memory creation rolls back its relational transaction when embedding or vector indexing fails, so an unindexed canonical row is not reported as successfully created.

### 4. Configuration & Secret Management
- All database credentials, JWT secrets, and CORS policies are parameterized through `.env.example` and Pydantic Settings.
- Restricted CORS origins for production while enabling local development flexibility.
- Docker Compose requires explicit PostgreSQL, Neo4j, and application secrets; predictable passwords are not used as deployment fallbacks.

### 5. Durable asynchronous processing
- Chat analysis is persisted in the relational `analysis_jobs` table before processing.
- Jobs are retried up to three attempts and retain failure details instead of disappearing with a request-scoped background task.
- Schema changes for graph fallback facts and analysis jobs are available through the Alembic migration chain.
