# MemOS — Ollama Integration & Local Proxy Guide

> **Target Platform:** Windows 10/11 & Local Development  
> **Default Ollama Endpoint:** `http://127.0.0.1:11434`  
> **MemOS Proxy Endpoint:** `http://127.0.0.1:11435/v1` (or `http://localhost:8000/v1`)

---

## 🌟 1-Button Ollama Desktop & Proxy Workflow

MemOS provides a streamlined, one-click integration flow for connecting with local Ollama instances and third-party AI client interfaces:

```mermaid
flowchart LR
    subgraph Client["Your PC / AI Client"]
        OD["Ollama Desktop / Open WebUI / Cursor"]
    end

    subgraph MemOS["MemOS Local Bridge (:11435 / :8000)"]
        PROXY["OpenAI Proxy Layer\n(/v1/chat/completions)"]
        CTX["Context Builder\n(Vector + Graph + Profile)"]
        MEM["Async Memory Capture"]
    end

    subgraph Storage["Persistent Multi-Store"]
        PG[("PostgreSQL\nMetadata")]
        QD[("Qdrant\nVectors")]
        NEO[("Neo4j\nKnowledge Graph")]
    end

    subgraph Engine["Local Inference Engine"]
        OLL["Ollama Local Server\n(:11434)"]
    end

    OD -->|1. Prompt| PROXY
    PROXY -->|2. Query| CTX
    CTX <-->|3. Retrieve| Storage
    CTX -->|4. Injected Context| OLL
    OLL -->|5. Token Stream (SSE)| PROXY
    PROXY -->|6. Token Stream| OD
    PROXY -.->|7. Asynchronous Capture| MEM
    MEM --> Storage
```

---

## 🛠️ Step-by-Step Connection Instructions

### Step 1: Detect Local Ollama
MemOS automatically queries `http://127.0.0.1:11434/api/tags` and `http://127.0.0.1:11434/api/version`.  
In the Next.js Web UI, the top **Ollama Desktop & Local Proxy Bridge** panel indicates:
- Server status (`● Connected` vs `○ Offline`)
- Latency (ms)
- Installed model list

### Step 2: Start the Windows Local Bridge
Run the bridge script to monitor ports and route traffic:
```powershell
.\scripts\start_bridge.bat
```
Or with Python:
```powershell
python scripts/memos_bridge.py
```

### Step 3: Connect Your Favorite AI Clients

#### 1. Open WebUI / LibreChat / Jan / Chatbox
- **API Base URL**: `http://127.0.0.1:11435/v1` (or `http://localhost:8000/v1`)
- **API Key**: `memos-local` (any string)
- **Model**: Select any installed model (e.g. `qwen3.5:9b`, `llama3:latest`)

#### 2. Cursor / VS Code Continue Extension
Configure your `config.json`:
```json
{
  "models": [
    {
      "title": "MemOS Ollama Qwen",
      "provider": "openai",
      "model": "qwen3.5:9b",
      "apiBase": "http://127.0.0.1:11435/v1",
      "apiKey": "memos-local"
    }
  ]
}
```

#### 3. Terminal & PowerShell
Push memories directly from shell sessions:
```powershell
.\scripts\save_memory.ps1 -Content "MemOS stores vectors in Qdrant and knowledge triples in Neo4j."
```
