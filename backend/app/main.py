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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "documentation": "/docs"
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

