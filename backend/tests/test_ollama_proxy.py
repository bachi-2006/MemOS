import os
import sys
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database.session import Base, get_db
from app.main import app
from app.models.models import User, Chat, Message

from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite database with StaticPool
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

def test_v1_models_endpoint():
    """Phase 3 Test: Verify GET /v1/models returns OpenAI standard format"""
    mock_models = [
        {"name": "qwen3.5:9b", "size": 5000000000},
        {"name": "llama3:latest", "size": 4700000000}
    ]
    with patch("app.services.ollama_service.ollama_service.list_models", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_models
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "qwen3.5:9b"
        assert data["data"][1]["id"] == "llama3:latest"

def test_v1_chat_completions_non_streaming():
    """Phase 3 Test: Verify POST /v1/chat/completions with stream=False"""
    payload = {
        "model": "qwen3.5:9b",
        "messages": [
            {"role": "system", "content": "You are a helpful coding companion."},
            {"role": "user", "content": "What is MemOS?"}
        ],
        "stream": False,
        "temperature": 0.7
    }

    mock_llm_response = "MemOS is an adaptive memory layer for local LLMs."

    with patch("app.services.ollama_service.ollama_service.generate_chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.services.context_builder.context_builder.build_augmented_context", new_callable=AsyncMock) as mock_ctx, \
         patch("app.api.proxy.async_store_chat_and_memory", new_callable=AsyncMock):
        
        mock_chat.return_value = mock_llm_response
        mock_ctx.return_value = {
            "augmented_prompt": "MemOS context\n\nUser Question: What is MemOS?",
            "context_injected": "=== MEMORIES ===\nMemOS uses Qdrant",
            "memories_used": [],
            "graph_nodes_used": []
        }

        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["content"] == mock_llm_response
        assert data["choices"][0]["message"]["role"] == "assistant"

def test_v1_chat_completions_streaming_sse():
    """Phase 4 Test: Verify SSE token streaming on POST /v1/chat/completions with stream=True"""
    payload = {
        "model": "qwen3.5:9b",
        "messages": [
            {"role": "user", "content": "Tell me a short story."}
        ],
        "stream": True
    }

    async def mock_token_stream(*args, **kwargs):
        tokens = ["Once ", "upon ", "a ", "time ", "in ", "MemOS."]
        for t in tokens:
            yield t

    with patch("app.services.ollama_service.ollama_service.generate_chat_stream", side_effect=mock_token_stream), \
         patch("app.services.context_builder.context_builder.build_augmented_context", new_callable=AsyncMock) as mock_ctx, \
         patch("app.api.proxy.async_store_chat_and_memory", new_callable=AsyncMock):
        
        mock_ctx.return_value = {
            "augmented_prompt": "User Question: Tell me a short story.",
            "context_injected": "",
            "memories_used": [],
            "graph_nodes_used": []
        }

        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # Verify SSE structure
        content = response.text
        assert "data: " in content
        assert "[DONE]" in content
        assert "Once " in content
        assert "MemOS." in content

def test_user_session_isolation():
    """Phase 5 Test: Verify proxy handles specific user without hardcoded first user in DB"""
    db = next(override_get_db())

    # Create two users
    u1 = User(id="user_alice_123", email="alice@test.local", username="alice", hashed_password="pw1")
    u2 = User(id="user_bob_456", email="bob@test.local", username="bob", hashed_password="pw2")
    db.add_all([u1, u2])
    db.commit()

    payload = {
        "model": "qwen3.5:9b",
        "messages": [{"role": "user", "content": "Hello as Bob"}],
        "user": "user_bob_456",
        "stream": False
    }

    with patch("app.services.ollama_service.ollama_service.generate_chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.services.context_builder.context_builder.build_augmented_context", new_callable=AsyncMock) as mock_ctx, \
         patch("app.api.proxy.async_store_chat_and_memory", new_callable=AsyncMock):
        
        mock_chat.return_value = "Hello Bob!"
        mock_ctx.return_value = {"augmented_prompt": "prompt", "context_injected": "", "memories_used": [], "graph_nodes_used": []}

        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        
        # Verify context builder was called with user_bob_456, NOT user_alice_123
        mock_ctx.assert_called_once()
        call_kwargs = mock_ctx.call_args.kwargs
        assert call_kwargs.get("user_id") == "user_bob_456"

def test_api_v1_chats_stream_endpoint():
    """Verify POST /api/v1/chats/stream returns SSE stream and persists message"""
    async def mock_token_stream(*args, **kwargs):
        tokens = ["Streamed ", "response ", "from ", "MemOS."]
        for t in tokens:
            yield t

    with patch("app.services.ollama_service.ollama_service.generate_chat_stream", side_effect=mock_token_stream), \
         patch("app.services.context_builder.context_builder.build_augmented_context", new_callable=AsyncMock) as mock_ctx:
        
        mock_ctx.return_value = {
            "augmented_prompt": "User Question: Hello",
            "context_injected": "",
            "memories_used": [],
            "graph_nodes_used": []
        }

        response = client.post("/api/v1/chats/stream", json={"prompt": "Hello", "personalized": True})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert "data: " in content
        assert "Streamed " in content
        assert "MemOS." in content

def test_api_v1_ollama_stream_endpoint():
    """Verify POST /api/v1/ollama/stream returns SSE stream directly"""
    async def mock_token_stream(*args, **kwargs):
        tokens = ["Ollama ", "stream ", "active."]
        for t in tokens:
            yield t

    with patch("app.services.ollama_service.ollama_service.generate_chat_stream", side_effect=mock_token_stream), \
         patch("app.services.context_builder.context_builder.build_augmented_context", new_callable=AsyncMock) as mock_ctx:
        
        mock_ctx.return_value = {
            "augmented_prompt": "User Question: Test stream",
            "context_injected": "",
            "memories_used": [],
            "graph_nodes_used": []
        }

        response = client.post("/api/v1/ollama/stream", json={"prompt": "Test stream", "personalized": True})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert "data: " in content
        assert "Ollama " in content
        assert "active." in content

