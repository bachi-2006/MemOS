from fastapi import APIRouter, Depends
from app.services.ollama_service import ollama_service
from app.schemas.schemas import ChatRequest, MemoryShareHook
from app.api.deps import get_current_user_optional
from app.models.models import User
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.services.context_builder import context_builder

from app.services.memory_service import memory_service

router = APIRouter(prefix="/ollama", tags=["Ollama Integration"])

@router.get("/status")
async def get_ollama_status():
    """
    Phase 1: Deep health & status detection endpoint for local Ollama server.
    Returns connection status, models found, active model, version, latency.
    """
    status = await ollama_service.get_status()
    return status

@router.get("/models")
async def get_models():
    """List available local Ollama models with real details."""
    models = await ollama_service.list_models()
    return {"models": models}

@router.post("/chat")
async def chat_with_ollama(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Feature 2: Direct chat endpoint with optional Personalized Responses toggle.
    When request.personalized is True:
      Builds and injects optimized context (Memories, Graph, Profile, Projects, Pinned memories).
    When request.personalized is False:
      Behaves exactly like standard raw Ollama.
    """
    final_prompt = request.prompt
    system_ctx = request.system_context
    context_meta = {}

    if request.personalized:
        context_res = await context_builder.build_augmented_context(
            db=db,
            user_id=current_user.id,
            user_prompt=request.prompt,
            top_k=5,
            active_project=request.active_project
        )
        final_prompt = context_res["augmented_prompt"]
        context_meta = {
            "memories_used": context_res["memories_used"],
            "graph_nodes_used": context_res["graph_nodes_used"],
            "context_injected": context_res["context_injected"]
        }

    response_text = await ollama_service.generate_chat(
        prompt=final_prompt,
        model=request.model,
        system_context=system_ctx
    )

    return {
        "response": response_text,
        "personalized": request.personalized,
        "explanation": context_meta
    }


@router.post("/share-memory")
async def share_memory_from_ollama_app(
    payload: MemoryShareHook,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Hook endpoint compatible with Ollama local clients / apps.
    Triggered when user clicks 'Share Memory' or triggers local memory ingestion.
    """
    memory = await memory_service.create_and_index_memory(
        db=db,
        user_id=current_user.id,
        content=payload.content,
        source=payload.source or "ollama_app_hook",
        tags=payload.tags or ["external_hook"]
    )
    return {
        "status": "success",
        "message": "Memory received and indexed into Postgres and Qdrant",
        "memory_id": memory.id,
        "received_content": memory.content,
        "source": memory.source
    }

