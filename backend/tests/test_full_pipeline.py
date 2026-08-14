import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.database.session import Base
from app.models.models import User, MemoryModel, UserProfile
from app.services.memory_service import memory_service
from app.services.conflict_service import conflict_engine
from app.services.lifecycle_service import lifecycle_engine
from app.api.dashboard import get_dashboard_metrics

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

def test_conflict_detection_and_resolution():
    async def run():
        db = next(get_test_db())
        user = User(email="conflict@memos.ai", username="conflictuser", hashed_password="pw")
        db.add(user)
        db.commit()

        # Add existing memory
        mem = MemoryModel(user_id=user.id, content="User prefers Python over TypeScript for backend services", status="active")
        db.add(mem)
        db.commit()

        with patch("app.services.ollama_service.ollama_service.generate_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "CONFLICT: Memory ID 1 | Explanation: New memory states user prefers Node.js for backend services."
            res = await conflict_engine.detect_and_resolve_conflicts(db, user.id, "User prefers Node.js for backend services")
            assert res["conflict_detected"] is True
            assert "CONFLICT:" in res["analysis"]

    asyncio.run(run())

def test_lifecycle_compression_and_forgetting():
    async def run():
        db = next(get_test_db())
        user = User(email="lifecycle@memos.ai", username="lifecycleuser", hashed_password="pw")
        db.add(user)
        db.commit()

        # Create old active memories (> 30 days old)
        old_time = datetime.utcnow() - timedelta(days=45)
        m1 = MemoryModel(user_id=user.id, content="Old chat memory 1", created_at=old_time, status="active", importance_score=0.2)
        m2 = MemoryModel(user_id=user.id, content="Old chat memory 2", created_at=old_time, status="active", importance_score=0.1)
        db.add_all([m1, m2])
        db.commit()

        with patch("app.services.ollama_service.ollama_service.generate_chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.ollama_service.ollama_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
             patch("app.services.qdrant_service.qdrant_service.upsert_memory_vector"), \
             patch("app.services.qdrant_service.qdrant_service.set_memory_status") as mock_set_status:

            mock_chat.return_value = "Compressed summary of old chat memories."
            mock_embed.return_value = [0.1] * 768

            # Compress
            compressed_count = await lifecycle_engine.compress_old_memories(db, user.id, days_threshold=30)
            assert compressed_count == 2
            assert m1.status == "archived"
            assert m2.status == "archived"

            # Adaptive Forgetting
            forgotten_count = lifecycle_engine.adaptive_forgetting(db, user.id, min_importance_threshold=0.3)
            assert forgotten_count == 2
            assert m1.status == "forgotten"
            assert m2.status == "forgotten"

    asyncio.run(run())

def test_dashboard_metrics_calculation():
    db = next(get_test_db())
    user = User(email="dashboard@memos.ai", username="dashuser", hashed_password="pw")
    db.add(user)
    db.commit()

    m1 = MemoryModel(user_id=user.id, content="Active memory", status="active", importance_score=1.5, confidence_score=0.9)
    m2 = MemoryModel(user_id=user.id, content="Archived memory", status="archived", importance_score=1.0, confidence_score=0.8)
    db.add_all([m1, m2])
    db.commit()

    metrics = get_dashboard_metrics(db=db, current_user=user)
    assert metrics["total_memories"] == 2
    assert metrics["active_memories"] == 1
    assert metrics["archived_memories"] == 1
    assert metrics["compression_ratio"] == "50.0%"
    assert "85.0%" in metrics["retrieval_accuracy"] or "90.0%" in metrics["retrieval_accuracy"]
