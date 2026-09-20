try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as rest_models
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    QdrantClient = None
    rest_models = None

from typing import List, Dict, Any, Optional
from app.core.config import settings

class QdrantService:
    def __init__(self):
        self.collection_name = "memory_vectors"
        self.client = None
        # Test seam / standalone fallback: an in-process vector backend that
        # implements the same upsert/search/delete contract as a live Qdrant
        # server. Activated automatically when Qdrant is unavailable.
        self._local_backend = None
        self._standalone_mode: bool = False

    def use_local_backend(self, backend):
        """Activate an in-process vector store for offline/functional tests."""
        from app.services.local_vector_store import LocalVectorStore
        self._local_backend = backend or LocalVectorStore()

    def clear_local_backend(self):
        self._local_backend = None

    def _client_or_backend(self):
        """Return the active store implementation: local backend or live Qdrant."""
        if self._local_backend is not None:
            return self._local_backend
        return self.get_client()

    def get_client(self):
        if not HAS_QDRANT:
            # qdrant-client not installed — activate in-process fallback
            if not self._local_backend:
                from app.services.local_vector_store import LocalVectorStore
                self._local_backend = LocalVectorStore()
                self._standalone_mode = True
                print("[QdrantService] qdrant-client not installed. Running in standalone in-process vector mode.")
            return None
        if not self.client:
            try:
                self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
                self._ensure_collection()
            except Exception as e:
                print(f"Qdrant connection notice: {e}")
                # Server unreachable — activate in-process fallback
                if not self._local_backend:
                    from app.services.local_vector_store import LocalVectorStore
                    self._local_backend = LocalVectorStore()
                    self._standalone_mode = True
                    print("[QdrantService] Qdrant server offline. Switched to in-process vector store.")
                return None
        return self.client

    def is_standalone_mode(self) -> bool:
        """Returns True when running with the in-process LocalVectorStore fallback."""
        return self._standalone_mode


    def _ensure_collection(self, vector_size: int = 768):
        """Ensure Qdrant vector collection exists"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest_models.VectorParams(
                    size=vector_size,
                    distance=rest_models.Distance.COSINE
                )
            )

    def upsert_memory_vector(
        self,
        memory_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ):
        if self._local_backend is not None:
            self._local_backend.upsert(memory_id, vector, payload)
            return
        client = self.get_client()
        if self._local_backend is not None:
            self._local_backend.upsert(memory_id, vector, payload)
            return
        if not client:
            raise RuntimeError("Qdrant vector store is unavailable")
        # Handle dynamic vector dimensions if first creation
        if vector:
            self._ensure_collection(vector_size=len(vector))
        client.upsert(
            collection_name=self.collection_name,
            points=[
                rest_models.PointStruct(
                    id=memory_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

    def search_similar_memories(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int = 5,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if self._local_backend is not None:
            return self._local_backend.search(query_vector, user_id, limit, project)
        client = self.get_client()
        if not client or not query_vector:
            return []

        try:
            must_conditions = [
                rest_models.FieldCondition(
                    key="user_id",
                    match=rest_models.MatchValue(value=user_id)
                ),
                rest_models.FieldCondition(
                    key="status",
                    match=rest_models.MatchValue(value="active")
                )
            ]
            # Optional project-scoped filtering (Step 2.4)
            if project:
                must_conditions.append(
                    rest_models.FieldCondition(
                        key="project",
                        match=rest_models.MatchValue(value=project)
                    )
                )

            search_filter = rest_models.Filter(must=must_conditions)

            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit
            )

            return [
                {
                    "memory_id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            print(f"Qdrant search notice: {e}")
            return []

    def delete_memory_vector(self, memory_id: str):
        """Phase 11: Hard deletion of vector from Qdrant to prevent ghost memories."""
        if self._local_backend is not None:
            self._local_backend.delete(memory_id)
            return
        client = self.get_client()
        if self._local_backend is not None:
            self._local_backend.delete(memory_id)
            return
        if not client:
            raise RuntimeError("Qdrant vector store is unavailable")
        client.delete(
            collection_name=self.collection_name,
            points_selector=rest_models.PointIdsList(points=[memory_id])
        )

    def set_memory_status(self, memory_id: str, status: str):
        if self._local_backend is not None:
            self._local_backend.set_payload(memory_id, {"status": status})
            return
        client = self.get_client()
        if not client:
            return
        try:
            client.set_payload(
                collection_name=self.collection_name,
                payload={"status": status},
                points=[memory_id]
            )
        except Exception as e:
            print(f"Qdrant set_payload notice: {e}")

    def set_importance_score(self, memory_id: str, importance_score: float):
        """Synchronize an importance score update from PostgreSQL into Qdrant."""
        if self._local_backend is not None:
            self._local_backend.set_payload(memory_id, {"importance_score": float(importance_score)})
            return
        client = self.get_client()
        if not client:
            return
        try:
            client.set_payload(
                collection_name=self.collection_name,
                payload={"importance_score": float(importance_score)},
                points=[memory_id]
            )
        except Exception as e:
            print(f"Qdrant set_importance_score notice: {e}")

qdrant_service = QdrantService()
