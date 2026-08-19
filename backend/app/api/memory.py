from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user_optional
from app.models.models import User, MemoryModel
from app.schemas.schemas import MemorySchema, MemoryShareHook, AnalyzeChatRequest, AnalyzeChatResponse
from app.services.memory_service import memory_service
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/memory", tags=["Memory Management & Search"])

@router.get("/search")
async def search_memories(
    query: str = Query(..., description="Query text for semantic search"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Semantic vector search against Qdrant memory collection (Phase 6)"""
    results = await memory_service.search_memories(
        db=db,
        user_id=current_user.id,
        query=query,
        limit=limit
    )
    return {"query": query, "results": results}

@router.post("/store", response_model=MemorySchema)
async def store_memory(
    payload: MemoryShareHook,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Store explicit canonical memory and trigger embedding indexing pipeline (Phase 5)"""
    memory = await memory_service.create_and_index_memory(
        db=db,
        user_id=current_user.id,
        content=payload.content,
        source=payload.source,
        tags=payload.tags
    )
    return memory

@router.get("/all")
def get_user_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """List canonical memories stored in PostgreSQL"""
    memories = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id).order_by(MemoryModel.created_at.desc()).all()
    return memories

@router.post("/analyze-chat", response_model=AnalyzeChatResponse)
async def analyze_chat_endpoint(
    request: AnalyzeChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Feature 1: 🧠 Analyze Chat Endpoint.
    Analyzes current conversation messages/chat, filters small talk, extracts facts/entities/projects/skills,
    deduplicates memories, updates importance/confidence scores, updates Neo4j graph & Qdrant vectors.
    """
    messages_payload = None
    if request.messages:
        messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]

    result = await analysis_service.analyze_chat(
        db=db,
        user_id=current_user.id,
        chat_id=request.chat_id,
        messages_input=messages_payload
    )
    return result

@router.post("/optimize")
async def optimize_memory_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Phase 10: 🧹 Optimize Memory / 🧠 Analyze Memory Store.
    Sweeps existing stored memories, applies importance recalculation, compression,
    adaptive forgetting, and conflict detection.
    """
    result = await analysis_service.optimize_memory_store(
        db=db,
        user_id=current_user.id
    )
    return result

@router.delete("/{memory_id}")
async def delete_memory_endpoint(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Phase 11: Unified Multi-Store Memory Deletion.
    Deletes memory across PostgreSQL, Qdrant vectors, and Neo4j knowledge graph.
    """
    success = await memory_service.delete_memory_unified(
        db=db,
        user_id=current_user.id,
        memory_id=memory_id
    )
    if not success:
        return {"status": "error", "message": "Memory not found or could not be deleted."}
    return {"status": "success", "message": f"Memory {memory_id} deleted across all stores."}

