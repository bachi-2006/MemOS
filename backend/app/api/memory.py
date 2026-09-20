from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user_optional
from app.models.models import User, MemoryModel
from app.schemas.schemas import MemorySchema, MemoryShareHook, AnalyzeChatRequest, AnalyzeChatResponse
from app.services.memory_service import memory_service
from app.services.analysis_service import analysis_service
from app.services.importance_service import importance_engine
from app.services.qdrant_service import qdrant_service

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

@router.post("/search")
async def search_memories_post(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Semantic vector search with POST body"""
    query = payload.get("query", "")
    limit = int(payload.get("limit", 5))
    results = await memory_service.search_memories(
        db=db,
        user_id=current_user.id,
        query=query,
        limit=limit
    )
    return results

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
    current_user: User = Depends(get_current_user_optional),
    limit: int = Query(50, ge=1, le=200, description="Max memories to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status: Optional[str] = Query(None, description="Filter by status: active, archived, compressed"),
    collection: Optional[str] = Query(None, description="Filter by collection name"),
):
    """Paginated, filterable listing of canonical memories from PostgreSQL."""
    q = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id)
    if status:
        q = q.filter(MemoryModel.status == status)
    if collection:
        q = q.filter(MemoryModel.collection == collection)
    return q.order_by(MemoryModel.created_at.desc()).offset(offset).limit(limit).all()


@router.patch("/{memory_id}/pin")
def toggle_pin_memory(
    memory_id: str,
    pinned: bool = Query(..., description="Set to true to pin, false to unpin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Toggle pinned status on a memory and recalculate its importance score.
    Pinned memories receive a +2.0 importance bonus that survives lifecycle sweeps.
    """
    mem = db.query(MemoryModel).filter(
        MemoryModel.id == memory_id,
        MemoryModel.user_id == current_user.id
    ).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem.is_pinned = pinned
    mem.importance_score = importance_engine.calculate_importance(mem, is_pinned=pinned)
    db.commit()
    db.refresh(mem)
    # Sync updated importance score to Qdrant payload
    try:
        qdrant_service.set_importance_score(memory_id, mem.importance_score)
    except Exception as e:
        print(f"Qdrant pin sync notice: {e}")
    return {"status": "ok", "memory_id": memory_id, "is_pinned": pinned, "importance_score": mem.importance_score}


@router.patch("/{memory_id}")
async def update_memory_content(
    memory_id: str,
    content: str = Body(..., embed=True, description="Updated memory content text"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Update the text content of a memory and re-index its embedding in Qdrant."""
    from app.services.ollama_service import ollama_service
    mem = db.query(MemoryModel).filter(
        MemoryModel.id == memory_id,
        MemoryModel.user_id == current_user.id
    ).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem.content = content
    db.commit()
    db.refresh(mem)
    # Re-embed and update Qdrant vector + payload
    try:
        embedding = await ollama_service.generate_embedding(content)
        if embedding:
            qdrant_service.upsert_memory_vector(
                memory_id=memory_id,
                vector=embedding,
                payload={
                    "memory_id": memory_id,
                    "user_id": current_user.id,
                    "content": content,
                    "importance_score": mem.importance_score,
                    "source": mem.source,
                    "status": mem.status,
                    "created_at": mem.created_at.isoformat(),
                    "project": getattr(mem, "project", None),
                    "collection": getattr(mem, "collection", None),
                    "is_pinned": bool(getattr(mem, "is_pinned", False)),
                }
            )
    except Exception as e:
        print(f"Qdrant re-embed notice: {e}")
    return {"status": "ok", "memory_id": memory_id}

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
    try:
        success = await memory_service.delete_memory_unified(
            db=db,
            user_id=current_user.id,
            memory_id=memory_id
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        ) from e
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Memory not found or could not be deleted.",
        )
    return {"status": "success", "message": f"Memory {memory_id} deleted across all stores."}
