import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.models import User, MemoryModel
from app.services.memory_service import memory_service

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_memory_creation_indexes_all_stores():
    """Creating a memory should write to the canonical DB + Qdrant (all guards present)."""
    async def run():
        db = next(get_test_db())
        user = User(email="cre1@memos.ai", username="cre1", hashed_password="pw")
        db.add(user)
        db.commit()

        with patch("app.services.ollama_service.ollama_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
             patch("app.services.qdrant_service.qdrant_service.upsert_memory_vector") as mock_upsert:
            mock_embed.return_value = [0.1] * 768
            mem = await memory_service.create_and_index_memory(db, user.id, "Test memory across stores", source="test")

            # Canonical PostgreSQL row exists
            stored = db.query(MemoryModel).filter(MemoryModel.id == mem.id).first()
            assert stored is not None
            assert stored.status == "active"

            # Qdrant upsert called once (embedding indexed)
            mock_upsert.assert_called_once()

    asyncio.run(run())


def test_memory_creation_rolls_back_when_indexing_fails():
    """A failed vector write must not leave a canonical unindexed memory row."""
    async def run():
        db = next(get_test_db())
        user = User(email="cre-fail@memos.ai", username="cre_fail", hashed_password="pw")
        db.add(user)
        db.commit()

        with patch("app.services.ollama_service.ollama_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
             patch(
                 "app.services.qdrant_service.qdrant_service.upsert_memory_vector",
                 side_effect=RuntimeError("qdrant unavailable"),
             ):
            mock_embed.return_value = [0.1] * 768
            with pytest.raises(RuntimeError, match="qdrant unavailable"):
                await memory_service.create_and_index_memory(
                    db, user.id, "Memory that must not be orphaned", source="test"
                )

        assert db.query(MemoryModel).filter(
            MemoryModel.user_id == user.id,
            MemoryModel.content == "Memory that must not be orphaned",
        ).first() is None

    asyncio.run(run())


def test_memory_deletion_propagates_to_all_stores():
    """Deleting a memory should remove the PostgreSQL row and attempt Qdrant + Neo4j cleanup."""
    async def run():
        db = next(get_test_db())
        user = User(email="del1@memos.ai", username="del1", hashed_password="pw")
        db.add(user)
        db.commit()

        mem = MemoryModel(
            user_id=user.id, content="Memory to delete", status="active",
            entities=[{"name": "Python", "type": "Technology"}]
        )
        db.add(mem)
        db.commit()
        db.refresh(mem)
        mem_id = mem.id

        with patch("app.services.qdrant_service.qdrant_service.delete_memory_vector") as mock_qdel, \
             patch("app.services.graph_service.graph_service.delete_fact") as mock_gdel:

            result = await memory_service.delete_memory_unified(db, user.id, mem_id)

            assert result is True
            mock_qdel.assert_called_once_with(mem_id)
            mock_gdel.assert_called_once()

            # No ghost row remains in PostgreSQL
            assert db.query(MemoryModel).filter(MemoryModel.id == mem_id).first() is None

    asyncio.run(run())


def test_memory_deletion_aborts_if_dependent_store_fails():
    """If a dependent store cleanup fails, deletion must abort so no ghost remains in PG."""
    async def run():
        db = next(get_test_db())
        user = User(email="del2@memos.ai", username="del2", hashed_password="pw")
        db.add(user)
        db.commit()

        mem = MemoryModel(
            user_id=user.id, content="Memory that cannot be fully deleted", status="active",
            entities=[{"name": "FastAPI", "type": "Technology"}]
        )
        db.add(mem)
        db.commit()
        db.refresh(mem)
        mem_id = mem.id

        with patch("app.services.qdrant_service.qdrant_service.delete_memory_vector",
                   side_effect=Exception("qdrant down")) as mock_qdel, \
             patch("app.services.graph_service.graph_service.delete_fact"):

            with pytest.raises(RuntimeError):
                await memory_service.delete_memory_unified(db, user.id, mem_id)

            # The canonical memory must STILL exist (delete was aborted to avoid ghost)
            assert db.query(MemoryModel).filter(MemoryModel.id == mem_id).first() is not None

    asyncio.run(run())


def test_importance_update_syncs_qdrant():
    """update_all_importance_scores should sync changed scores into Qdrant."""
    from datetime import datetime, timedelta
    from app.services.importance_service import importance_engine

    db = next(get_test_db())
    user = User(email="sync1@memos.ai", username="sync1", hashed_password="pw")
    db.add(user)
    db.commit()

    old = datetime.utcnow() - timedelta(days=10)
    mem = MemoryModel(user_id=user.id, content="Aging memory", created_at=old,
                      access_count=0, entities=[], status="active", importance_score=1.0)
    db.add(mem)
    db.commit()

    with patch("app.services.qdrant_service.qdrant_service.set_importance_score") as mock_sync:
        importance_engine.update_all_importance_scores(db, user.id)
        # Score recomputed to a different value -> Qdrant sync triggered at least once
        db.refresh(mem)
        assert mem.importance_score != 1.0
        mock_sync.assert_called()
