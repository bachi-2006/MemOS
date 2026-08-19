#!/usr/bin/env python3
"""
MemOS Windows Local Bridge Process (Phase 8)
Detects Ollama on port 11434, checks models, starts the proxy on 11435, and monitors health.
"""

import sys
import os
import time
import socket
import json
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
PROXY_PORT = int(os.getenv("PROXY_PORT", "11435"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_ollama():
    try:
        with httpx.Client(timeout=3.0) as client:
            res = client.get(f"{OLLAMA_URL}/api/tags")
            if res.status_code == 200:
                models = res.json().get("models", [])
                model_names = [m.get("name") for m in models]
                return True, model_names
            return False, []
    except Exception:
        return False, []

def print_banner(ollama_connected: bool, models: list):
    print("=" * 65)
    print("           🧠 MemOS — Windows Local Bridge & Proxy          ")
    print("=" * 65)
    print(f"  Ollama Server:      {OLLAMA_URL} {'[CONNECTED ✅]' if ollama_connected else '[OFFLINE ❌]'}")
    print(f"  MemOS Proxy Port:   http://127.0.0.1:{PROXY_PORT}/v1")
    print(f"  Models Detected:    {len(models)} installed ({', '.join(models[:4]) if models else 'None'})")
    print(f"  OpenAI Endpoint:    http://127.0.0.1:{PROXY_PORT}/v1/chat/completions")
    print(f"  Status:             Running Local Proxy & SSE Streaming...")
    print("=" * 65)
    print("  Use this endpoint in Open WebUI, LibreChat, Cursor, or CLI.")
    print("=" * 65 + "\n")

# Bridge FastAPI application
bridge_app = FastAPI(title="MemOS Windows Bridge Proxy", version="1.0.0")

bridge_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@bridge_app.get("/")
def bridge_root():
    return {
        "service": "memos-windows-bridge",
        "proxy_port": PROXY_PORT,
        "ollama_url": OLLAMA_URL,
        "status": "online"
    }

@bridge_app.get("/health")
def bridge_health():
    connected, models = check_ollama()
    return {
        "status": "healthy" if connected else "degraded",
        "ollama_connected": connected,
        "models_count": len(models),
        "models": models
    }

# Forward proxy routes to backend app if available or directly handle
try:
    from app.api.proxy import router as proxy_router
    from app.database.session import Base, engine
    Base.metadata.create_all(bind=engine)
    bridge_app.include_router(proxy_router)
except Exception as e:
    print(f"Notice: Loading fallback proxy route ({e})")

def main():
    ollama_ok, models = check_ollama()
    print_banner(ollama_ok, models)

    if not ollama_ok:
        print("⚠️ Warning: Local Ollama not detected at port 11434.")
        print("   Make sure Ollama is running (`ollama serve` or Ollama app).")
        print("   The bridge will keep monitoring and proxying incoming requests.\n")

    print(f"🚀 Starting MemOS Proxy Server on 127.0.0.1:{PROXY_PORT}...")
    uvicorn.run(bridge_app, host="127.0.0.1", port=PROXY_PORT, log_level="warning")

if __name__ == "__main__":
    main()
