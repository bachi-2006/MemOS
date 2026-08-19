try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as rest_models
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    QdrantClient = None
    rest_models = None

from typing import List, Dict, Any
from app.core.config import settings

class QdrantService:
    def __init__(self):
        self.collection_name = "memory_vectors"
        self.client = None

    def get_client(self):
        if not HAS_QDRANT:
            return None
        if not self.client:
            try:
                self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
                self._ensure_collection()
            except Exception as e:
                print(f"Qdrant connection notice: {e}")
                return None
        return self.client


    def _ensure_collection(self, vector_size: int = 768):
        """Ensure Qdrant vector collection exists"""
        try:
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
        except Exception as e:
            print(f"Qdrant collection setup notice/error: {e}")

    def upsert_memory_vector(
        self,
        memory_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ):
        client = self.get_client()
        if not client:
            return
        # Handle dynamic vector dimensions if first creation
        if vector:
            self._ensure_collection(vector_size=len(vector))
            
        try:
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
        except Exception as e:
            print(f"Qdrant upsert notice: {e}")

    def search_similar_memories(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        client = self.get_client()
        if not client or not query_vector:
            return []

        try:
            search_filter = rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="user_id",
                        match=rest_models.MatchValue(value=user_id)
                    ),
                    rest_models.FieldCondition(
                        key="status",
                        match=rest_models.MatchValue(value="active")
                    )
                ]
            )

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
        client = self.get_client()
        if not client:
            return
        try:
            client.delete(
                collection_name=self.collection_name,
                points_selector=rest_models.PointIdsList(points=[memory_id])
            )
        except Exception as e:
            print(f"Qdrant delete notice: {e}")

    def set_memory_status(self, memory_id: str, status: str):
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

qdrant_service = QdrantService()
