from sqlalchemy.orm import Session
from typing import Dict, Any
from app.models.models import MemoryModel
from app.services.ollama_service import ollama_service

class ConflictResolutionEngine:
    async def detect_and_resolve_conflicts(
        self,
        db: Session,
        user_id: str,
        new_memory_content: str
    ) -> Dict[str, Any]:
        """
        Detects contradictory facts between existing memories and new memory input.
        Phase 11 Research Contribution.
        """
        active_memories = db.query(MemoryModel).filter(
            MemoryModel.user_id == user_id,
            MemoryModel.status == "active"
        ).order_by(MemoryModel.created_at.desc()).limit(20).all()

        if not active_memories:
            return {"conflict_detected": False}

        existing_texts = "\n".join([f"- ID {m.id}: {m.content}" for m in active_memories])

        prompt = f"""
Given the existing user memories:
{existing_texts}

New statement: "{new_memory_content}"

Does the new statement contradict any existing memory?
If YES, respond in format: CONFLICT: <Memory ID> | Explanation: <reason>
If NO, respond: NO CONFLICT
"""
        response = await ollama_service.generate_chat(prompt=prompt)

        if "CONFLICT:" in response:
            return {
                "conflict_detected": True,
                "analysis": response
            }

        return {"conflict_detected": False, "analysis": "No conflict detected."}

conflict_engine = ConflictResolutionEngine()
