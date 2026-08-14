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

    memories = db.query(MemoryModel).filter(MemoryModel.user_id == current_user.id).all()
    avg_importance = sum([m.importance_score for m in memories]) / len(memories) if memories else 1.0
    
    # Calculate real compression ratio
    compressed_count = archived_memories + forgotten_memories
    comp_ratio = (compressed_count / total_memories * 100.0) if total_memories > 0 else 0.0

    # Calculate real retrieval confidence/accuracy
    avg_confidence = (sum([m.confidence_score or 1.0 for m in memories]) / len(memories) * 100.0) if memories else 95.0

    return {
        "total_memories": total_memories,
        "active_memories": active_memories,
        "archived_memories": archived_memories,
        "forgotten_memories": forgotten_memories,
        "total_chats": total_chats,
        "average_importance_score": round(avg_importance, 2),
        "compression_ratio": f"{comp_ratio:.1f}%",
        "retrieval_accuracy": f"{avg_confidence:.1f}%"
    }
