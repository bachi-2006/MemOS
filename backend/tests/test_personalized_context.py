import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import Base
from app.models.models import User, MemoryModel, UserProfile
from app.services.context_builder import context_builder

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

def test_context_builder_augmentation():
    async def run_test():
        db = next(get_test_db())

        user = User(email="context_user@memos.ai", username="ctx_user", hashed_password="pw")
        db.add(user)
        db.commit()

        # Add user profile
        profile = UserProfile(
            user_id=user.id,
            preferred_languages=["Python", "TypeScript"],
            preferred_frameworks=["FastAPI", "Next.js"],
            skills=["Full Stack", "Vector Search"],
            writing_style="Concise and architectural",
            current_projects=["MemOS"]
        )
        db.add(profile)

        # Add pinned memory
        pinned_mem = MemoryModel(
            user_id=user.id,
            content="Critical decision: MemOS runs 100% locally with Qdrant and Neo4j.",
            is_pinned=True,
            status="active"
        )
        db.add(pinned_mem)
        db.commit()

        with patch("app.services.memory_service.memory_service.search_memories", new_callable=AsyncMock) as mock_vector_search, \
             patch("app.services.graph_service.graph_service.get_user_graph") as mock_graph:
            
            mock_vector_search.return_value = [
                {"memory_id": "m1", "score": 0.92, "payload": {"content": "User prefers dark mode UI", "project": "MemOS"}}
            ]
            mock_graph.return_value = {
                "nodes": [{"id": "FastAPI", "label": "FastAPI", "type": "Technology"}],
                "edges": [{"source": "MemOS", "relationship": "USES", "target": "FastAPI"}]
            }

            result = await context_builder.build_augmented_context(
                db=db,
                user_id=user.id,
                user_prompt="How do I structure the API routes?",
                top_k=5
            )

            assert "=== USER PROFILE & PREFERENCES ===" in result["augmented_prompt"]
            assert "Python, TypeScript" in result["augmented_prompt"]
            assert "=== ACTIVE PROJECTS ===" in result["augmented_prompt"]
            assert "=== PINNED MEMORIES ===" in result["augmented_prompt"]
            assert "=== RELEVANT LONG-TERM MEMORIES ===" in result["augmented_prompt"]
            assert "=== KNOWLEDGE GRAPH CONTEXT ===" in result["augmented_prompt"]
            assert len(result["memories_used"]) >= 1

    asyncio.run(run_test())
