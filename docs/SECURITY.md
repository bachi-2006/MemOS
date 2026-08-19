# MemOS — Security, Privacy & Isolation Model

> **Local-First Security Policy:** Ensuring on-device privacy, session isolation, and secure local development.

---

## 🔒 Security Principles

### 1. User & Session Isolation (No Hardcoded Fallbacks)
- Resolved the historical `db.query(User).first()` pattern.
- The proxy and memory ingestion layers resolve user profiles based on request identity (`user`, `x-user-id`, or deterministic companion profile).
- Prevents cross-contamination of memory spaces across different local sessions or user profiles.

### 2. Zero Unnecessary Cloud Exfiltration
- All embedding generation (`nomic-embed-text`) and inference (`qwen3.5:9b`, `llama3`, `mistral`) are executed via the local Ollama instance (`127.0.0.1:11434`).
- No conversation transcripts, memory vectors, or graph triples are dispatched to third-party cloud APIs.

### 3. Unified Deletion & Memory Sanitation
- Deletion is cross-synchronized across PostgreSQL, Qdrant, and Neo4j.
- Eliminates "ghost memories" where a deleted record in relational storage remains discoverable via vector or graph queries.

### 4. Configuration & Secret Management
- All database credentials, JWT secrets, and CORS policies are parameterized through `.env.example` and Pydantic Settings.
- Restricted CORS origins for production while enabling local development flexibility.
