import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.session import Base, get_db
from app.main import app
from app.models.models import User, MemoryModel, Chat, Message, UserProfile
from app.services.context_builder import context_builder

# Setup in-memory SQLite database with StaticPool for strict isolation tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

from app.api.deps import get_current_user_optional

def test_multi_tenant_chat_isolation():
    """Security Test: Verify User A cannot access User B's private chat sessions"""
    db = next(override_get_db())

    # Create User A and User B
    user_a = User(id="user_alice_security", email="alice_sec@test.local", username="alice_sec", hashed_password="pw")
    user_b = User(id="user_bob_security", email="bob_sec@test.local", username="bob_sec", hashed_password="pw")
    db.add_all([user_a, user_b])
    db.commit()

    # Create Chat belonging to Alice
    alice_chat = Chat(id="chat_alice_secret_1", user_id=user_a.id, title="Alice Secret Chat")
    db.add(alice_chat)
    db.commit()

    # Bob attempts to fetch Alice's messages
    app.dependency_overrides[get_current_user_optional] = lambda: user_b
    try:
        response = client.get(f"/api/v1/chats/{alice_chat.id}/messages")
        assert response.status_code == 404
        assert response.json()["detail"] == "Chat session not found"
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

def test_multi_tenant_memory_search_isolation():
    """Security Test: Verify Qdrant memory search enforces user_id boundaries"""
    db = next(override_get_db())
    user_a = db.query(User).filter(User.id == "user_alice_security").first()

    app.dependency_overrides[get_current_user_optional] = lambda: user_a
    try:
        with patch("app.services.memory_service.memory_service.search_memories", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [{"memory_id": "mem_1", "content": "Alice private note", "score": 0.95}]
            
            response = client.get("/api/v1/memory/search?query=private")
            assert response.status_code == 200
            
            mock_search.assert_called_once()
            call_kwargs = mock_search.call_args.kwargs
            assert call_kwargs.get("user_id") == user_a.id
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

def test_context_builder_user_isolation():
    """Security Test: Verify ContextBuilder strictly filters user profile and pinned items by user_id"""
    db = next(override_get_db())

    user_a = db.query(User).filter(User.id == "user_alice_security").first()
    user_b = db.query(User).filter(User.id == "user_bob_security").first()

    # Alice Profile & Memory
    prof_a = UserProfile(user_id=user_a.id, preferred_languages=["Haskell", "Rust"])
    mem_a = MemoryModel(id="mem_a_pin", user_id=user_a.id, content="Alice Secret Project X", is_pinned=True, status="active")

    # Bob Profile & Memory
    prof_b = UserProfile(user_id=user_b.id, preferred_languages=["PHP", "Java"])
    mem_b = MemoryModel(id="mem_b_pin", user_id=user_b.id, content="Bob Secret Budget 2026", is_pinned=True, status="active")

    db.add_all([prof_a, mem_a, prof_b, mem_b])
    db.commit()

    async def run_test():
        with patch("app.services.memory_service.memory_service.search_memories", new_callable=AsyncMock) as mock_search, \
             patch("app.services.graph_service.graph_service.get_user_graph") as mock_graph:
            
            mock_search.return_value = []
            mock_graph.return_value = {"nodes": [], "edges": []}

            # Build context for Alice
            res_alice = await context_builder.build_augmented_context(
                db=db,
                user_id=user_a.id,
                user_prompt="Help me write code"
            )

            # Assert Alice gets ONLY Alice's profile and pinned memory
            assert "Haskell, Rust" in res_alice["augmented_prompt"]
            assert "Alice Secret Project X" in res_alice["augmented_prompt"]
            assert "PHP, Java" not in res_alice["augmented_prompt"]
            assert "Bob Secret Budget 2026" not in res_alice["augmented_prompt"]

    asyncio.run(run_test())
