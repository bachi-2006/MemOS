"""In-process vector store used as a test seam for QdrantService.

Implements the same contract as a live Qdrant collection (upsert/search/delete/
set_payload) using real cosine-similarity arithmetic with user_id + status
filtering, so retrieval and lifecycle code paths genuinely execute against real
vector math without requiring a running Qdrant server.
"""
import math
from typing import Dict, List, Any, Optional


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: List[float]) -> float:
    return math.sqrt(_dot(v, v))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)


class LocalVectorStore:
    def __init__(self):
        # memory_id -> {"vector": [...], "payload": {...}}
        self.points: Dict[str, Dict[str, Any]] = {}

    def upsert(self, memory_id: str, vector: List[float], payload: Dict[str, Any]):
        self.points[memory_id] = {"vector": vector, "payload": dict(payload)}

    def delete(self, memory_id: str):
        self.points.pop(memory_id, None)

    def set_payload(self, memory_id: str, payload: Dict[str, Any]):
        if memory_id in self.points:
            self.points[memory_id]["payload"].update(payload)

    def get_payload(self, memory_id: str) -> Optional[Dict[str, Any]]:
        point = self.points.get(memory_id)
        return point["payload"] if point else None

    def search(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int = 5,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        from datetime import datetime
        now_iso = datetime.utcnow().isoformat()
        scored = []
        for memory_id, point in self.points.items():
            payload = point["payload"]
            if payload.get("user_id") != user_id:
                continue
            if payload.get("status") != "active":
                continue
            if project and payload.get("project") and payload.get("project") != project:
                continue
            valid_until = payload.get("valid_until")
            if valid_until and valid_until < now_iso:
                continue
            score = cosine_similarity(query_vector, point["vector"])
            scored.append(
                {
                    "memory_id": memory_id,
                    "score": score,
                    "payload": payload,
                }
            )
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:limit]

    def count(self) -> int:
        return len(self.points)
