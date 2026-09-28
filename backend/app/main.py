import sys
import os
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure backend root is on sys.path for direct module resolution
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from app.core.config import settings
from app.database.session import engine, Base
from app.api import auth, ollama, chats, memory, graph, dashboard, proxy, profile
from app.workers.scheduler import start_scheduler, scheduler

# Create database tables automatically
Base.metadata.create_all(bind=engine)

def _run_migrations():
    """Apply Alembic migrations to keep database schema automatically synchronized with model definitions."""
    try:
        from alembic.config import Config
        from alembic import command
        from sqlalchemy import inspect
        import os
        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        if os.path.exists(alembic_ini_path):
            cfg = Config(alembic_ini_path)
            cfg.set_main_option("sqlalchemy.url", str(engine.url))
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if "alembic_version" not in tables and "memories" in tables:
                command.stamp(cfg, "head")
            else:
                command.upgrade(cfg, "head")
    except Exception as e:
        if "already exists" not in str(e).lower():
            print(f"[Alembic] Automatic migration notice: {e}")

_run_migrations()

def _rehydrate_vector_store():
    """Auto-rehydrate in-process LocalVectorStore from SQLite on startup so embeddings persist across restarts."""
    from app.services.qdrant_service import qdrant_service
    from app.models.models import MemoryModel
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        active_mems = db.query(MemoryModel).filter(
            MemoryModel.status == "active",
            MemoryModel.embedding != None
        ).all()
        count = 0
        for m in active_mems:
            if m.embedding and isinstance(m.embedding, list):
                payload = {
                    "memory_id": m.id,
                    "user_id": m.user_id,
                    "content": m.content,
                    "importance_score": m.importance_score,
                    "source": m.source,
                    "status": m.status,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "project": m.project,
                    "collection": m.collection,
                    "is_pinned": bool(m.is_pinned),
                    "valid_from": m.valid_from.isoformat() if m.valid_from else None,
                    "valid_until": m.valid_until.isoformat() if m.valid_until else None,
                }
                qdrant_service.upsert_memory_vector(
                    memory_id=m.id,
                    vector=m.embedding,
                    payload=payload
                )
                count += 1
        if count > 0:
            print(f"[VectorStore] Rehydrated {count} persistent memory embeddings from SQLite into vector index.")
    except Exception as e:
        print(f"[VectorStore] Rehydration notice: {e}")
    finally:
        db.close()

OLLAMA = settings.OLLAMA_BASE_URL or "http://127.0.0.1:11434"
_client: httpx.AsyncClient | None = None

def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=None)
    return _client

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _rehydrate_vector_store()
    except Exception as e:
        print(f"[Lifespan] Vector rehydration notice: {e}")
    try:
        start_scheduler()
        print("APScheduler started successfully for Phase 14 memory lifecycle tasks.")
    except Exception as e:
        print(f"Failed to start scheduler: {e}")
    yield
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler shut down cleanly.")
    global _client
    if _client:
        await _client.aclose()
        _client = None

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MemOS: An Adaptive Memory Lifecycle Management Framework for Persistent LLM Agents",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS middleware - explicit origins only, no credentials on wildcard
clean_origins = [o for o in settings.ALLOWED_ORIGINS if o != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=clean_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# -----------------------------------------------------------------------------
# Phase 13 & 14: Subsystem Health & API Status Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/health")
async def api_health():
    online = False
    version = ""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(OLLAMA + "/api/tags")
            online = r.status_code == 200
            if online:
                version = (r.json() or {}).get("version", "")
    except Exception:
        pass
    return {
        "ok": True,
        "ollama": online,
        "version": version,
        "port": settings.PROXY_PORT or 8000,
        "architecture": "Unified MemOS Multi-Store Core"
    }

@app.get("/health/ollama")
async def health_ollama():
    from app.services.ollama_service import ollama_service
    status = await ollama_service.get_status()
    return status

@app.get("/health/postgres")
@app.get("/health/database")
def health_database():
    import time
    from sqlalchemy import text
    start = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "database", "status": "connected", "latency_ms": latency}
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "database", "status": "disconnected", "latency_ms": latency, "error": str(e)}

@app.get("/health/qdrant")
def health_qdrant():
    import time
    from app.services.qdrant_service import qdrant_service
    start = time.time()
    try:
        client = qdrant_service.get_client()
        if client:
            client.get_collections()
            latency = round((time.time() - start) * 1000, 1)
            return {"service": "qdrant", "status": "connected", "latency_ms": latency}
        else:
            return {"service": "qdrant", "status": "standalone_fallback", "notice": "Using in-process local vector store"}
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "qdrant", "status": "standalone_fallback", "latency_ms": latency, "notice": str(e)}

@app.get("/health/neo4j")
def health_neo4j():
    import time
    from app.services.graph_service import graph_service
    start = time.time()
    try:
        driver = graph_service.get_driver()
        if driver:
            with driver.session() as session:
                session.run("RETURN 1")
            latency = round((time.time() - start) * 1000, 1)
            return {"service": "neo4j", "status": "connected", "latency_ms": latency}
        else:
            return {"service": "neo4j", "status": "disconnected", "notice": "Driver unavailable or running in standalone"}
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "neo4j", "status": "disconnected", "latency_ms": latency, "error": str(e)}

@app.get("/health/redis")
def health_redis():
    import time
    start = time.time()
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        r.ping()
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "redis", "status": "connected", "latency_ms": latency}
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "redis", "status": "disconnected", "latency_ms": latency, "error": str(e)}

@app.get("/health")
async def health_aggregate():
    ollama_res = await health_ollama()
    pg_res = health_database()
    qd_res = health_qdrant()
    neo_res = health_neo4j()
    rd_res = health_redis()

    overall = "healthy"
    if not ollama_res.get("connected") or pg_res.get("status") != "connected":
        overall = "degraded"

    return {
        "status": overall,
        "services": {
            "ollama": ollama_res,
            "database": pg_res,
            "qdrant": qd_res,
            "neo4j": neo_res,
            "redis": rd_res
        }
    }

# -----------------------------------------------------------------------------
# Ollama Direct Streaming Proxy Endpoints
# -----------------------------------------------------------------------------
async def _ollama_proxy(path: str, request: Request):
    body = await request.body()
    streaming = False
    try:
        streaming = bool(json.loads(body).get("stream"))
    except Exception:
        streaming = request.headers.get("accept", "").startswith("application/x-ndjson")

    client = _get_client()

    if streaming:
        async def gen():
            async with client.stream(
                "POST", OLLAMA + path, content=body,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status_code != 200:
                    _txt = (await resp.aread())[:300].decode("utf-8", "ignore")
                    yield (json.dumps({"error": f"HTTP {resp.status_code}: {_txt}"}) + "\n").encode()
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk

        return StreamingResponse(gen(), media_type="application/x-ndjson")

    resp = await client.post(
        OLLAMA + path, content=body, headers={"Content-Type": "application/json"}
    )
    try:
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception:
        return JSONResponse(status_code=resp.status_code, content={"error": resp.text[:300]})

@app.post("/api/ollama/chat")
async def proxy_chat(request: Request):
    return await _ollama_proxy("/api/chat", request)

@app.post("/api/ollama/embed")
async def proxy_embed(request: Request):
    return await _ollama_proxy("/api/embed", request)

@app.post("/api/ollama/generate")
async def proxy_generate(request: Request):
    return await _ollama_proxy("/api/generate", request)

async def _ollama_get(path: str):
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(OLLAMA + path)
            return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception:
        return JSONResponse(status_code=502, content={"error": "ollama unreachable"})

@app.get("/api/ollama/tags")
async def proxy_tags():
    return await _ollama_get("/api/tags")

@app.get("/api/ollama/ps")
async def proxy_ps():
    return await _ollama_get("/api/ps")

# Include all API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(ollama.router, prefix=settings.API_V1_STR)
app.include_router(chats.router, prefix=settings.API_V1_STR)
app.include_router(memory.router, prefix=settings.API_V1_STR)
app.include_router(graph.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(profile.router, prefix=settings.API_V1_STR)
app.include_router(proxy.router)

# -----------------------------------------------------------------------------
# Static Single Page App (SPA) Serving
# -----------------------------------------------------------------------------
DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

@app.get("/", include_in_schema=False)
async def index():
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html", headers=NO_CACHE_HEADERS)
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "proxy_port": settings.PROXY_PORT,
        "documentation": "/docs"
    }

@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str):
    if full_path.startswith(("docs", "redoc", "openapi.json", "api/", "health/")):
        return JSONResponse(status_code=404, content={"error": "Not Found"})
    target = DIST / full_path
    if target.is_file():
        return FileResponse(target)
    # Prevent falling back to index.html for missing asset files
    if full_path.startswith("assets/") or full_path.endswith((".js", ".css", ".map", ".ico", ".png", ".jpg", ".svg", ".json")):
        return JSONResponse(status_code=404, content={"error": "Asset not found"})
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html", headers=NO_CACHE_HEADERS)
    return JSONResponse(status_code=404, content={"error": "Frontend dist not built"})
