"""Live-Ollama functional retrieval test.

This test uses the REAL Ollama embedding service (no local fallback, no mocks)
against the real in-process vector store so genuine semantic retrieval runs.

It is skipped automatically unless:
  - MEMOS_TEST_LIVE_OLLAMA=1 is set in the environment, AND
  - a live Ollama instance is reachable at settings.OLLAMA_BASE_URL.

Run with a real Ollama up:
  set MEMOS_TEST_LIVE_OLLAMA=1
  pytest backend/tests/test_live_ollama_retrieval.py -v
"""
import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.services.qdrant_service import qdrant_service
from app.services.ollama_service import ollama_service
from app.services.local_vector_store import LocalVectorStore
from app.services.memory_service import memory_service

_HAS_LIVE = None


def _ollama_live() -> bool:
    global _HAS_LIVE
    if _HAS_LIVE is None:
        try:
            _HAS_LIVE = asyncio.run(ollama_service.get_status()).get("connected", False)
        except Exception:
            _HAS_LIVE = False
    return _HAS_LIVE


requires_live_ollama = pytest.mark.skipif(
    not os.environ.get("MEMOS_TEST_LIVE_OLLAMA", "0") in {"1", "true", "True"},
    reason="Set MEMOS_TEST_LIVE_OLLAMA=1 and run a live Ollama to enable.",
)


@requires_live_ollama
def test_live_ollama_retrieval_is_available():
    assert _ollama_live(), "Ollama reported not connected; start it before running."


@requires_live_ollama
def test_real_ollama_embeddings_and_retrieval():
    if not _ollama_live():
        pytest.skip("Ollama unreachable")
    assert _ollama_live(), "Ollama reported not connected"

    vector_store = LocalVectorStore()
    qdrant_service.use_local_backend(vector_store)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    user_id = "live_ollama_user"
    query_text = "What database does the user prefer for vector search?"

    memories_to_store = [
        "The user prefers Qdrant vector database for semantic search.",
        "The user drinks black coffee every morning.",
        "The user runs ten kilometers before breakfast.",
    ]

    stored_ids = []
    loop = asyncio.new_event_loop()
    try:
        for content in memories_to_store:
            m = loop.run_until_complete(
                memory_service.create_and_index_memory(db, user_id, content, source="live_ollama")
            )
            stored_ids.append(m.id)

        # Real Ollama embedding for the query.
        query_vec = loop.run_until_complete(ollama_service.generate_embedding(query_text))
        assert query_vec, "Ollama returned no embedding for the query"

        results = vector_store.search(query_vec, user_id, limit=3)
        assert results, "Retrieval returned no results"

        # The top retrieval should be the Qdrant/vector-database memory because
        # real semantic embeddings place it closest to the query.
        top = results[0]
        assert top["memory_id"] == stored_ids[0], (
            f"Expected the vector-database memory first, got {top['payload']['content']}"
        )
    finally:
        loop.close()
        db.close()
        Base.metadata.drop_all(bind=engine)
        qdrant_service.clear_local_backend()
