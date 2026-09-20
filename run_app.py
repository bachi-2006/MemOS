#!/usr/bin/env python3
"""
MemOS Unified Full-Stack Application Launcher
--------------------------------------------
Starts the unified MemOS cognitive engine serving both the backend REST/SSE/Ollama
APIs and the compiled React 18 SPA on a single local port (default 8000).

Usage:
  python run_app.py
  python run_app.py --port 8000
  python run_app.py --no-browser
  python run_app.py --test-only
"""

import sys
import os
import time
import socket
import argparse
import subprocess
import webbrowser
import threading
from pathlib import Path

# Add project root and backend to Python path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def check_python_version():
    if sys.version_info < (3, 10):
        print(f"[ERROR] MemOS requires Python 3.10+, found {sys.version}")
        sys.exit(1)


def check_dependencies():
    required = ["fastapi", "uvicorn", "httpx", "sqlalchemy", "pydantic"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[ERROR] Missing required Python packages: {', '.join(missing)}")
        print("Run: pip install -r backend/requirements.txt")
        sys.exit(1)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_available_port(preferred: int = 8000, max_attempts: int = 10) -> int:
    port = preferred
    for _ in range(max_attempts):
        if not is_port_in_use(port):
            return port
        port += 1
    return preferred


def check_and_warm_ollama():
    """Probe local Ollama daemon and pre-load embedding model into VRAM."""
    import httpx
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{ollama_url}/api/tags")
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                print(f"[Ollama] Detected {len(models)} installed models: {', '.join(models[:4])}")

                # Warm up nomic-embed-text if present
                embed_model = next((m for m in models if "embed" in m.lower()), None)
                if embed_model:
                    print(f"[Ollama] Warming up '{embed_model}' in VRAM...")
                    try:
                        w_resp = client.post(
                            f"{ollama_url}/api/embeddings",
                            # Use /api/embeddings (not deprecated /api/embed)
                            json={"model": embed_model, "prompt": "warmup"},
                            timeout=30.0
                        )
                        if w_resp.status_code == 200:
                            print(f"[Ollama] '{embed_model}' warmed up and ready.")
                    except Exception as we:
                        print(f"[Ollama] Warmup note: {we}")
                return True
    except Exception:
        pass

    print("[Ollama] Local Ollama server not detected on port 11434.")
    print("         MemOS will operate in Companion Standalone mode (IndexedDB + SQLite).")
    print("         To enable local inference: start Ollama (`ollama serve`).")
    return False


def verify_frontend():
    """Ensure the frontend dist bundle exists; build if missing."""
    index_html = FRONTEND_DIST / "index.html"
    if not index_html.is_file():
        print("[Frontend] Compiled web assets not found. Running `npm run build`...")
        try:
            cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            subprocess.run([cmd, "run", "build"], cwd=str(FRONTEND_DIR), check=True)
            print("[Frontend] Build completed successfully.")
        except Exception as e:
            print(f"[WARN] Failed to compile frontend automatically: {e}")
            print("       Please run `npm run build` inside frontend/.")


def run_smoke_tests(port: int):
    """Execute end-to-end endpoint verification against running server."""
    import httpx
    base_url = f"http://127.0.0.1:{port}"
    print(f"\n[SmokeTest] Probing MemOS Unified Gateway at {base_url}...")
    # Ensure Windows console does not throw UnicodeEncodeError
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    endpoints = [
        ("/", "SPA Web App"),
        ("/api/health", "Ollama & Gateway Status"),
        ("/health/database", "SQLite / Database"),
        ("/api/v1/dashboard/metrics", "Memory Analytics"),
        ("/api/v1/profile/", "User Profile"),
        ("/api/v1/graph/", "Knowledge Graph"),
        ("/api/v1/memory/all", "Memory Bank Store"),
        ("/docs", "OpenAPI Interactive Swagger"),
    ]

    all_passed = True
    with httpx.Client(timeout=5.0) as client:
        for path, desc in endpoints:
            try:
                r = client.get(f"{base_url}{path}")
                if r.status_code in (200, 304):
                    print(f"  [PASS] [{r.status_code}] {path:<28} - {desc}")
                else:
                    print(f"  [FAIL] [{r.status_code}] {path:<28} - {desc}")
                    all_passed = False
            except Exception as ex:
                print(f"  [ERR ] [---] {path:<28} - {desc}: {ex}")
                all_passed = False

    if all_passed:
        print("\n[SmokeTest] All 8 core endpoints passed! System 100% operational.\n")
    else:
        print("\n[SmokeTest] Some endpoints returned non-200 status.\n")
    return all_passed


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="MemOS Unified Full-Stack Application Launcher")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--test-only", action="store_true", help="Spin up server, verify endpoints, and exit")
    args = parser.parse_args()

    check_python_version()
    check_dependencies()

    print("=" * 68)
    print("  MemOS: Adaptive Memory Lifecycle Management & Agent Framework")
    print("  Unified Full-Stack Architecture | Single Port Runtime")
    print("=" * 68)

    check_and_warm_ollama()
    verify_frontend()

    chosen_port = args.port
    if is_port_in_use(chosen_port):
        alt_port = find_available_port(chosen_port + 1)
        print(f"[Port] Port {chosen_port} is in use. Selecting fallback port {alt_port}.")
        chosen_port = alt_port

    app_url = f"http://127.0.0.1:{chosen_port}"
    print(f"\n[Gateway] Starting unified server on: {app_url}")
    print(f"[Gateway] API Documentation:         {app_url}/docs")
    print(f"[Gateway] Architecture:              Multi-Store Memory + Neo4j + Qdrant + React 18\n")

    if args.test_only:
        import uvicorn
        from app.main import app as fastapi_app

        config = uvicorn.Config(app=fastapi_app, host="127.0.0.1", port=chosen_port, log_level="warning")
        server = uvicorn.Server(config)
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()

        time.sleep(2.0)
        passed = run_smoke_tests(chosen_port)
        server.should_exit = True
        server_thread.join(timeout=3.0)
        sys.exit(0 if passed else 1)

    # Launch browser after slight delay
    if not args.no_browser:
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(app_url)
            except Exception:
                pass
        threading.Thread(target=open_browser, daemon=True).start()

    # Also bind secondary port 5151 in background if available
    if chosen_port != 5151 and not is_port_in_use(5151):
        def run_5151():
            try:
                import uvicorn
                from app.main import app as fastapi_app
                cfg5151 = uvicorn.Config(app=fastapi_app, host="127.0.0.1", port=5151, log_level="warning")
                srv5151 = uvicorn.Server(cfg5151)
                srv5151.run()
            except Exception:
                pass
        threading.Thread(target=run_5151, daemon=True).start()
        print(f"[Gateway] Also listening on port 5151: http://127.0.0.1:5151")

    # Run Uvicorn directly
    import uvicorn
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=chosen_port, reload=False, log_level="info")
    except KeyboardInterrupt:
        print("\n[Shutdown] MemOS server gracefully stopped.")


if __name__ == "__main__":
    main()
