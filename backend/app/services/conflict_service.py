import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import MemoryModel
from app.services.ollama_service import ollama_service


class ConflictResolutionEngine:
    def _extract_id_from_response(self, response: str) -> Optional[str]:
        match = re.search(r'CONFLICT:\s*([a-zA-Z0-9\-_]+)', response, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate.upper() not in ("YES", "TRUE", "NONE", "NULL"):
                return candidate
        return None

    async def detect_and_resolve_conflicts(
        self,
        db: Session,
        user_id: str,
        new_memory_content: str
    ) -> Dict[str, Any]:
        """
        Detects contradictory facts between existing memories and new memory input.
        Phase 11 Research Contribution (Semantic Conflict Detection & Auto-Resolution).
        """
        from app.services.qdrant_service import qdrant_service

        candidate_mems = []
        try:
            query_vector = await ollama_service.generate_embedding(new_memory_content)
            if query_vector:
                similar = qdrant_service.search_similar_memories(query_vector, user_id, limit=10)
                similar_ids = [r["memory_id"] for r in similar if r.get("score", 0) > 0.6]
                if similar_ids:
                    candidate_mems = db.query(MemoryModel).filter(
                        MemoryModel.id.in_(similar_ids),
                        MemoryModel.user_id == user_id,
                        MemoryModel.status == "active"
                    ).all()
        except Exception as e:
            print(f"[ConflictResolution] Vector similarity search notice: {e}")

        # Fallback to recent chronological active memories if vector search found nothing
        if not candidate_mems:
            candidate_mems = db.query(MemoryModel).filter(
                MemoryModel.user_id == user_id,
                MemoryModel.status == "active"
            ).order_by(MemoryModel.created_at.desc()).limit(20).all()

        if not candidate_mems:
            return {"conflict_detected": False}

        existing_texts = "\n".join([f"- ID {m.id}: {m.content}" for m in candidate_mems])

        prompt = f"""Given the existing user memories:
{existing_texts}

New statement: "{new_memory_content}"

Does the new statement contradict any existing memory?
If YES, respond in format: CONFLICT: <Memory ID> | Explanation: <reason>
If NO, respond: NO CONFLICT
"""
        response = await ollama_service.generate_chat(prompt=prompt)

        if "CONFLICT:" in response:
            conflicting_id = self._extract_id_from_response(response)
            resolved = False
            if conflicting_id:
                old_mem = db.query(MemoryModel).filter(
                    MemoryModel.id == conflicting_id,
                    MemoryModel.user_id == user_id
                ).first()
                if old_mem and old_mem.status == "active":
                    old_mem.status = "archived"
                    tags = list(old_mem.tags or [])
                    if "superseded" not in tags:
                        tags.append("superseded")
                    old_mem.tags = tags
                    try:
                        qdrant_service.set_memory_status(old_mem.id, "archived")
                    except Exception as e:
                        print(f"Failed to update status in vector store: {e}")
                    db.commit()
                    resolved = True
            return {
                "conflict_detected": True,
                "resolved": resolved,
                "conflicting_id": conflicting_id,
                "analysis": response
            }

        return {"conflict_detected": False, "analysis": "No conflict detected."}


conflict_engine = ConflictResolutionEngine()
