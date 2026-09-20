from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user_optional
from app.models.models import User, MemoryModel, Chat

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])

@router.get("/metrics")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Phase 15 & 16: Analytics and Dashboard Card Metrics"""
    total_memories = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id).count()
    active_memories = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id, MemoryModel.status == "active").count()
    archived_memories = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id, MemoryModel.status == "archived").count()
    forgotten_memories = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id, MemoryModel.status == "forgotten").count()
    total_chats = db.query(Chat).filter(Chat.user_id == current_user.id).count()

    # Use SQL aggregates — avoids loading all memory rows into Python RAM
    from sqlalchemy import func
    agg = db.query(
        func.avg(MemoryModel.importance_score),
        func.avg(MemoryModel.confidence_score),
    ).filter(MemoryModel.user_id == current_user.id).one()
    avg_importance = float(agg[0] or 1.0)
    avg_confidence = float(agg[1] or 0.95) * 100.0

    # Calculate real compression ratio
    compressed_count = archived_memories + forgotten_memories
    comp_ratio = (compressed_count / total_memories * 100.0) if total_memories > 0 else 0.0

    return {
        "total_memories": total_memories,
        "active_memories": active_memories,
        "archived_memories": archived_memories,
        "forgotten_memories": forgotten_memories,
        "total_chats": total_chats,
        "average_importance_score": round(avg_importance, 2),
        "compression_ratio": f"{comp_ratio:.1f}%",
        "average_memory_confidence": round(avg_confidence, 1),
    }
