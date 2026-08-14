from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import MemoryModel

class ImportanceEngine:
    def calculate_importance(
        self,
        memory: MemoryModel,
        is_pinned: bool = False
    ) -> float:
        """
        Calculates memory importance score:
        Importance = Recency + Frequency + Entity Count + Confidence + User Pin
        """
        # Recency decay (days passed)
        now = datetime.utcnow()
        days_old = (now - memory.created_at).total_seconds() / 86400.0
        recency_score = max(0.1, 1.0 - (days_old * 0.05))

        # Access frequency weight
        frequency_score = min(2.0, 1.0 + (memory.access_count * 0.1))

        # Entity richness
        entity_count = len(memory.entities) if memory.entities else 0
        entity_score = min(1.5, 1.0 + (entity_count * 0.1))

        # Base confidence & Pin bonus
        confidence = memory.confidence_score or 1.0
        pin_bonus = 2.0 if is_pinned else 0.0

        total_score = (recency_score * 0.3) + (frequency_score * 0.3) + (entity_score * 0.2) + (confidence * 0.2) + pin_bonus
        return round(total_score, 3)

    def update_all_importance_scores(self, db: Session, user_id: str):
        memories = db.query(MemoryModel).filter(MemoryModel.user_id == user_id, MemoryModel.status == "active").all()
        for mem in memories:
            mem.importance_score = self.calculate_importance(mem)
        db.commit()

importance_engine = ImportanceEngine()
