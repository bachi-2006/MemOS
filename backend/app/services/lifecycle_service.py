from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.models import MemoryModel
from app.services.ollama_service import ollama_service
from app.services.memory_service import memory_service
from app.services.qdrant_service import qdrant_service

class LifecycleEngine:
    async def compress_old_memories(self, db: Session, user_id: str, days_threshold: int = 30):
        """Phase 12: Memory Compression Engine - Summarizes stale memories into compressed long-term notes via LLM"""
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        old_memories = db.query(MemoryModel).filter(
            MemoryModel.user_id == user_id,
            MemoryModel.status == "active",
            MemoryModel.created_at < cutoff
        ).all()

        if not old_memories:
            return 0

        # Extract text snippets
        mem_texts = [f"- {m.content}" for m in old_memories]
        combined_text = "\n".join(mem_texts)

        prompt = f"""
Compress and synthesize the following set of older user memories into a single concise, high-density long-term memory summary (2-3 sentences max):

MEMORIES:
{combined_text}
"""
        summary_note = await ollama_service.generate_chat(prompt=prompt)

        # Store compressed canonical note
        if summary_note and not summary_note.startswith("Failed"):
            await memory_service.create_and_index_memory(
                db=db,
                user_id=user_id,
                content=f"Compressed Archive: {summary_note.strip()}",
                source="lifecycle_compression",
                tags=["compressed_archive", "summary"],
                importance_score=1.2
            )

        # Transition individual old memories to archived
        for mem in old_memories:
            mem.status = "archived"
            qdrant_service.set_memory_status(mem.id, "archived")
        db.commit()

        return len(old_memories)

    def adaptive_forgetting(self, db: Session, user_id: str, min_importance_threshold: float = 0.3):
        """Phase 13: Adaptive Forgetting Engine - Transition low importance memories to forgotten status"""
        low_value_memories = db.query(MemoryModel).filter(
            MemoryModel.user_id == user_id,
            MemoryModel.importance_score < min_importance_threshold,
            MemoryModel.status == "archived"
        ).all()

        for mem in low_value_memories:
            mem.status = "forgotten"
            qdrant_service.set_memory_status(mem.id, "forgotten")
        db.commit()
        return len(low_value_memories)

lifecycle_engine = LifecycleEngine()
