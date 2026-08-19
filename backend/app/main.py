from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import engine, Base
from app.api import auth, ollama, chats, memory, graph, dashboard, proxy, profile

from contextlib import asynccontextmanager
from app.workers.scheduler import start_scheduler, scheduler

# Create database tables automatically
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        start_scheduler()
        print("APScheduler started successfully for Phase 14 memory lifecycle tasks.")
    except Exception as e:
        print(f"Failed to start scheduler: {e}")
    yield
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler shut down cleanly.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MemOS: An Adaptive Memory Lifecycle Management Framework for Persistent LLM Agents",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "proxy_port": settings.PROXY_PORT,
        "documentation": "/docs"
    }

# -----------------------------------------------------------------------------
# Phase 13: Granular Subsystem Health Endpoints
# -----------------------------------------------------------------------------

@app.get("/health/ollama")
async def health_ollama():
    from app.services.ollama_service import ollama_service
    status = await ollama_service.get_status()
    return status

@app.get("/health/postgres")
def health_postgres():
    import time
    from sqlalchemy import text
    start = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "postgresql", "status": "connected", "latency_ms": latency}
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "postgresql", "status": "disconnected", "latency_ms": latency, "error": str(e)}

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
            return {"service": "qdrant", "status": "disconnected", "notice": "Client unavailable"}
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        return {"service": "qdrant", "status": "disconnected", "latency_ms": latency, "error": str(e)}

@app.get("/health/neo4j")
def health_neo4j():
    import time
    from app.services.graph_service import graph_service
    start = time.time()
    try:
        driver = graph_service.get_driver()
        if driver:
            driver.verify_connectivity()
            latency = round((time.time() - start) * 1000, 1)
            return {"service": "neo4j", "status": "connected", "latency_ms": latency}
        else:
            return {"service": "neo4j", "status": "disconnected", "notice": "Driver unavailable"}
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
    pg_res = health_postgres()
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
            "postgresql": pg_res,
            "qdrant": qd_res,
            "neo4j": neo_res,
            "redis": rd_res
        }
    }

# Include all API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(ollama.router, prefix=settings.API_V1_STR)
app.include_router(chats.router, prefix=settings.API_V1_STR)
app.include_router(memory.router, prefix=settings.API_V1_STR)
app.include_router(graph.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(profile.router, prefix=settings.API_V1_STR)
app.include_router(proxy.router)

