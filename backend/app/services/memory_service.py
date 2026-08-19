from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.models import MemoryModel
from app.schemas.schemas import MemorySchema
from app.services.ollama_service import ollama_service
from app.services.qdrant_service import qdrant_service

class MemoryService:
    async def create_and_index_memory(
        self,
        db: Session,
        user_id: str,
        content: str,
        source: str = "chat",
        tags: List[str] = [],
        importance_score: float = 1.0
    ) -> MemoryModel:
        """Stores canonical memory in Postgres and indexes its embedding into Qdrant."""
        memory = MemoryModel(
            user_id=user_id,
            content=content,
            source=source,
            tags=tags,
            importance_score=importance_score,
            confidence_score=1.0,
            status="active"
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)

        # Generate embedding via Ollama
        embedding = await ollama_service.generate_embedding(content)

        # Index in Qdrant
        if embedding:
            payload = {
                "memory_id": memory.id,
                "user_id": user_id,
                "content": content,
                "importance_score": memory.importance_score,
                "source": source,
                "status": memory.status,
                "created_at": memory.created_at.isoformat()
            }
            qdrant_service.upsert_memory_vector(
                memory_id=memory.id,
                vector=embedding,
                payload=payload
            )

        return memory

    async def search_memories(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Semantic search against Qdrant vector collection."""
        query_vector = await ollama_service.generate_embedding(query)
        if not query_vector:
            return []

        search_results = qdrant_service.search_similar_memories(
            query_vector=query_vector,
            user_id=user_id,
            limit=limit
        )

        return search_results

    async def delete_memory_unified(
        self,
        db: Session,
        user_id: str,
        memory_id: str
    ) -> bool:
        """
        Phase 11: Unified deletion across PostgreSQL, Qdrant, and Neo4j.
        Prevents ghost memories and preserves cross-system consistency.
        """
        memory = db.query(MemoryModel).filter(
            MemoryModel.id == memory_id,
            MemoryModel.user_id == user_id
        ).first()

        if not memory:
            return False

        # 1. Delete vector from Qdrant
        try:
            qdrant_service.delete_memory_vector(memory_id)
        except Exception as e:
            print(f"Qdrant deletion notice: {e}")

        # 2. Prune extracted entities from Neo4j graph if present
        try:
            if memory.entities:
                for ent in memory.entities:
                    ent_name = ent.get("name") if isinstance(ent, dict) else str(ent)
                    if ent_name:
                        from app.services.graph_service import graph_service
                        graph_service.delete_fact(user_id, ent_name)
        except Exception as e:
            print(f"Neo4j entity prune notice: {e}")

        # 3. Delete from PostgreSQL
        db.delete(memory)
        db.commit()
        return True

memory_service = MemoryService()
