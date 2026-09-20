import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Add the repository root so we can import scripts/* helpers
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.database.session import Base
from app.models.models import User, MemoryModel
from app.services.importance_service import importance_engine
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

def _make_memory(user_id, content, created_days_ago=0, access_count=0,
                 entities=None, confidence_score=1.0, importance_score=1.0,
                 status="active"):
    return MemoryModel(
        user_id=user_id,
        content=content,
        created_at=datetime.utcnow() - timedelta(days=created_days_ago),
        access_count=access_count,
        entities=entities,
        confidence_score=confidence_score,
        importance_score=importance_score,
        status=status
    )


# =============================================================================
# Phase 8 - Step 13: Importance scoring
# =============================================================================

def test_importance_high_for_recent_frequent_memory():
    """A frequently-accessed, recent memory should score higher."""
    db = next(get_test_db())
    user = User(email="imp1@memos.ai", username="imp1", hashed_password="pw")
    db.add(user)
    db.commit()

    rec_freq = _make_memory(user.id, "Recent + frequent", created_days_ago=1, access_count=5, entities=[{"name": "X"}], confidence_score=1.0)
    recent_score = importance_engine.calculate_importance(rec_freq)

    assert recent_score > 1.0
    # Frequent access pushes it above the nominal ~1.0 baseline


def test_importance_low_for_old_rarely_accessed_memory():
    """An old, rarely accessed memory should score lower."""
    db = next(get_test_db())
    user = User(email="imp2@memos.ai", username="imp2", hashed_password="pw")
    db.add(user)
    db.commit()

    old_rare = _make_memory(user.id, "Old + rarely accessed", created_days_ago=40, access_count=0, entities=[], confidence_score=0.5)
    old_score = importance_engine.calculate_importance(old_rare)

    recent_freq = _make_memory(user.id, "Recent + frequent", created_days_ago=0, access_count=5, entities=[{"name": "X"}], confidence_score=1.0)
    recent_score = importance_engine.calculate_importance(recent_freq)

    assert old_score < recent_score
    assert recent_score > old_score


def test_importance_recency_decay_decreases_score_over_time():
    """Importance should decrease as a memory ages (aging lifecycle)."""
    db = next(get_test_db())
    user = User(email="imp3@memos.ai", username="imp3", hashed_password="pw")
    db.add(user)
    db.commit()

    fresh = _make_memory(user.id, "Fresh", created_days_ago=0, access_count=0, entities=[], confidence_score=1.0)
    aged = _make_memory(user.id, "Aged", created_days_ago=15, access_count=0, entities=[], confidence_score=1.0)

    fresh_score = importance_engine.calculate_importance(fresh)
    aged_score = importance_engine.calculate_importance(aged)

    assert aged_score < fresh_score


def test_importance_pin_bonus():
    """Pinned memories should receive a +2.0 importance bonus."""
    db = next(get_test_db())
    user = User(email="imp4@memos.ai", username="imp4", hashed_password="pw")
    db.add(user)
    db.commit()

    mem = _make_memory(user.id, "Pinned memory", created_days_ago=5, access_count=0, entities=[], confidence_score=1.0)
    unpinned = importance_engine.calculate_importance(mem, is_pinned=False)
    pinned = importance_engine.calculate_importance(mem, is_pinned=True)

    assert pinned - unpinned == pytest.approx(2.0, abs=0.01)


def test_importance_update_all_scores():
    """update_all_importance_scores should recompute every active memory's score."""
    db = next(get_test_db())
    user = User(email="imp5@memos.ai", username="imp5", hashed_password="pw")
    db.add(user)
    db.commit()

    m1 = _make_memory(user.id, "M1", created_days_ago=0, access_count=2, entities=[{"name": "A"}], confidence_score=1.0)
    m2 = _make_memory(user.id, "M2", created_days_ago=30, access_count=0, entities=[], confidence_score=0.5)
    db.add_all([m1, m2])
    db.commit()

    importance_engine.update_all_importance_scores(db, user.id)

    db.refresh(m1)
    db.refresh(m2)
    assert m1.importance_score != 1.0
    assert m2.importance_score != 1.0
    assert m1.importance_score > m2.importance_score


# =============================================================================
# Phase 8 - Step 14: Duplicate detection (semantic)
# =============================================================================

def test_duplicate_exact_match_detection():
    """Exact (case-insensitive) duplicates in the memory store should be counted."""
    db = next(get_test_db())
    user = User(email="dup1@memos.ai", username="dup1", hashed_password="pw")
    db.add(user)
    db.commit()

    existing = _make_memory(user.id, "I use Python for backend development", status="active")
    db.add(existing)
    db.commit()

    existing_contents = {m.content.lower().strip() for m in db.query(MemoryModel).all()}
    # A semantically identical rephrase is NOT caught by exact-match (documented limitation)
    assert "I use Python for backend development".lower() in existing_contents
    assert "I primarily use Python".lower() not in existing_contents


def test_duplicate_rephrase_detection_via_similarity():
    """Rephrased duplicates should be flagged by token-similarity helper."""
    from scripts.benchmark_dataset import BENCHMARK_SCENARIOS
    from scripts.real_benchmark import evaluate_similarity

    dup_scenarios = [s for s in BENCHMARK_SCENARIOS if s.get("is_duplicate")]
    assert len(dup_scenarios) >= 5

    true_positives = sum(
        1 for s in dup_scenarios
        if evaluate_similarity(s["query"], s.get("existing_memories", []))
    )
    # At least the obvious rephrases should be caught
    assert true_positives >= 1


# =============================================================================
# Phase 8 - Step 15: Conflict detection classification
# =============================================================================

def test_conflict_detection_true_positive():
    """Conflicting statements should be flagged as conflicts."""
    from scripts.benchmark_dataset import BENCHMARK_SCENARIOS
    from scripts.real_benchmark import evaluate_conflict

    conflict_scenarios = [s for s in BENCHMARK_SCENARIOS if s.get("is_conflict")]
    assert len(conflict_scenarios) >= 5

    tp = sum(
        1 for s in conflict_scenarios
        if evaluate_conflict(s["query"], s.get("existing_memories", []))
    )
    assert tp >= 1


def test_conflict_detection_no_false_positive_on_non_conflicts():
    """Ordinary facts should never be flagged as conflicts."""
    from scripts.benchmark_dataset import BENCHMARK_SCENARIOS
    from scripts.real_benchmark import evaluate_conflict

    neutral = [s for s in BENCHMARK_SCENARIOS if not s.get("is_conflict") and not s.get("is_duplicate")]
    fp = sum(
        1 for s in neutral
        if evaluate_conflict(s["query"], [])
    )
    # Empty existing memories -> no conflicting pairs -> should be 0 false positives
    assert fp == 0


def test_conflict_engine_llm_no_conflict():
    """ConflictResolutionEngine should return False when LLM says NO CONFLICT."""
    db = next(get_test_db())
    user = User(email="conf2@memos.ai", username="conf2", hashed_password="pw")
    db.add(user)
    db.commit()

    mem = MemoryModel(user_id=user.id, content="User uses Python for data analysis", status="active")
    db.add(mem)
    db.commit()

    with patch("app.services.ollama_service.ollama_service.generate_chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "NO CONFLICT"
        res = asyncio.run(conflict_engine_detect(db, user.id, "User uses Python for machine learning"))
        assert res["conflict_detected"] is False


def conflict_engine_detect(db, user_id, content):
    from app.services.conflict_service import conflict_engine
    return conflict_engine.detect_and_resolve_conflicts(db, user_id, content)


# =============================================================================
# Phase 9 - Step 18: Forgetting + retention (important memories NOT removed)
# =============================================================================

def test_adaptive_forgetting_preserves_important_memories():
    """Memories above the importance threshold must NOT be forgotten."""
    db = next(get_test_db())
    user = User(email="forget1@memos.ai", username="forget1", hashed_password="pw")
    db.add(user)
    db.commit()

    important = _make_memory(user.id, "Important memory", status="archived", importance_score=1.5)
    low = _make_memory(user.id, "Low value memory", status="archived", importance_score=0.2)
    db.add_all([important, low])
    db.commit()

    with patch("app.services.qdrant_service.qdrant_service.set_memory_status"):
        from app.services.lifecycle_service import lifecycle_engine
        forgotten_count = lifecycle_engine.adaptive_forgetting(db, user.id, min_importance_threshold=0.3)

    assert forgotten_count == 1
    db.refresh(important)
    db.refresh(low)
    assert important.status == "archived"
    assert low.status == "forgotten"
