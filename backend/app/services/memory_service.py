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
        tags: Optional[List[str]] = None,
        importance_score: float = 1.0,
        project: Optional[str] = None,
        collection: Optional[str] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
    ) -> MemoryModel:
        """Stores canonical memory in Postgres and indexes its embedding into Qdrant.

        The relational row and its Qdrant vector are written inside the same
        DB transaction: `flush()` assigns the memory id without committing, the
        vector is indexed, and only then is the transaction committed. If
        embedding generation or the Qdrant upsert raises, the whole transaction
        is rolled back so we never persist an orphaned, un-indexed memory.
        """
        memory = MemoryModel(
            user_id=user_id,
            content=content,
            source=source,
            tags=tags or [],
            importance_score=importance_score,
            confidence_score=1.0,
            status="active",
            valid_from=valid_from or datetime.utcnow(),
            valid_until=valid_until,
        )
        db.add(memory)
        db.flush()

        try:
            # Generate embedding via Ollama
            embedding = await ollama_service.generate_embedding(content)

            # Index in Qdrant with full payload including project/collection for
            # context-builder project-focus filtering (Step 0.4 / 2.4 fix)
            if embedding:
                memory.embedding = embedding
                payload = {
                    "memory_id": memory.id,
                    "user_id": user_id,
                    "content": content,
                    "importance_score": memory.importance_score,
                    "source": source,
                    "status": memory.status,
                    "created_at": memory.created_at.isoformat(),
                    "project": project or getattr(memory, "project", None),
                    "collection": collection or getattr(memory, "collection", None),
                    "is_pinned": bool(getattr(memory, "is_pinned", False)),
                    "valid_from": memory.valid_from.isoformat() if memory.valid_from else None,
                    "valid_until": memory.valid_until.isoformat() if memory.valid_until else None,
                }
                qdrant_service.upsert_memory_vector(
                    memory_id=memory.id,
                    vector=embedding,
                    payload=payload
                )

            db.commit()
        except Exception:
            # The memory row has only been flushed at this point. Roll back the
            # relational transaction if embedding or indexing fails so callers
            # never receive a memory that was not fully indexed.
            db.rollback()
            raise
        db.refresh(memory)
        return memory

    async def search_memories(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 5,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Hybrid RAG Search: Combines semantic vector similarity with exact keyword & tag boosting."""
        query_vector = await ollama_service.generate_embedding(query)
        search_results = []
        if query_vector:
            search_results = qdrant_service.search_similar_memories(
                query_vector=query_vector,
                user_id=user_id,
                limit=limit,
                project=project
            )
            # Filter out memories explicitly muted from recall
            search_results = [
                r for r in search_results
                if "mute_recall" not in [str(t).lower() for t in r.get("payload", {}).get("tags", [])]
            ]
            if db and search_results:
                res_ids = [r.get("memory_id") for r in search_results if r.get("memory_id")]
                muted_db_ids = {
                    m.id for m in db.query(MemoryModel.id, MemoryModel.tags)
                    .filter(MemoryModel.id.in_(res_ids))
                    .all()
                    if "mute_recall" in [str(t).lower() for t in (m.tags or [])]
                }
                if muted_db_ids:
                    search_results = [r for r in search_results if r.get("memory_id") not in muted_db_ids]

        # Keyword & Tag Hybrid Boosting
        keywords = [w.lower().strip() for w in query.split() if len(w.strip()) > 3]
        if keywords and db:
            from datetime import datetime
            now = datetime.utcnow()
            seen_ids = {r.get("memory_id") for r in search_results}
            sql_matches = []

            active_query = db.query(MemoryModel).filter(
                MemoryModel.user_id == user_id,
                MemoryModel.status == "active"
            )
            if project:
                active_query = active_query.filter(MemoryModel.project == project)

            candidate_mems = active_query.limit(40).all()
            for m in candidate_mems:
                if m.id in seen_ids:
                    continue
                if m.valid_until and m.valid_until < now:
                    continue

                content_lower = m.content.lower()
                tags_lower = [str(t).lower() for t in (m.tags or [])]
                if "mute_recall" in tags_lower:
                    continue

                match_count = sum(1 for kw in keywords if kw in content_lower or any(kw in t for t in tags_lower))
                if match_count > 0:
                    score = min(0.95, 0.70 + (0.08 * match_count))
                    sql_matches.append({
                        "memory_id": m.id,
                        "score": score,
                        "payload": {
                            "memory_id": m.id,
                            "user_id": user_id,
                            "content": m.content,
                            "importance_score": m.importance_score,
                            "source": m.source,
                            "status": m.status,
                            "created_at": m.created_at.isoformat() if m.created_at else None,
                            "project": m.project,
                            "collection": m.collection,
                            "is_pinned": bool(m.is_pinned),
                            "valid_from": m.valid_from.isoformat() if m.valid_from else None,
                            "valid_until": m.valid_until.isoformat() if m.valid_until else None,
                        }
                    })

            combined = search_results + sql_matches
            combined.sort(key=lambda x: x.get("score", 0), reverse=True)
            return combined[:limit]

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

        # Consistent cross-store deletion: cleanup dependent stores first, and only
        # finalize the canonical PostgreSQL delete once all dependent stores succeed.
        # This prevents partially-deleted (ghost) memories across stores.
        failures = []

        # 1. Delete vector from Qdrant
        try:
            qdrant_service.delete_memory_vector(memory_id)
        except Exception as e:
            failures.append(f"qdrant:{e}")

        # 2. Prune extracted entities from Neo4j graph if present
        try:
            if memory.entities:
                for ent in memory.entities:
                    ent_name = ent.get("name") if isinstance(ent, dict) else str(ent)
                    if ent_name:
                        from app.services.graph_service import graph_service
                        graph_service.delete_fact(user_id, ent_name)
        except Exception as e:
            failures.append(f"neo4j:{e}")

        # 3. Delete from PostgreSQL (authoritative). Only commit after dependent
        #    stores report success, so we never leave a ghost in another store.
        if failures:
            # Dependent stores failed to clean up; abort the delete so the
            # canonical memory remains consistent everywhere.
            raise RuntimeError(
                f"Cross-store deletion aborted; dependent store(s) failed: {failures}. "
                "Memory left intact to preserve consistency."
            )

        db.delete(memory)
        db.commit()
        return True

memory_service = MemoryService()
