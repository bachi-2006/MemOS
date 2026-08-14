import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.models import User, MemoryModel, UserProfile, Message, Chat
from app.services.analysis_service import analysis_service


# Setup in-memory SQLite database for unit tests
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

def test_json_parsing_and_fallback():
    raw_llm_json = """
    Here is the analysis result:
    {
        "summary": "Discussed building MemOS companion app for Ollama Desktop using FastAPI and Next.js.",
        "facts": ["MemOS uses Qdrant for vectors", "Neo4j is used for Knowledge Graph"],
        "entities": [{"name": "Qdrant", "type": "Technology", "related_to": "MemOS", "relationship": "USES"}],
        "projects": ["MemOS"],
        "technologies": ["FastAPI", "Next.js", "Qdrant", "Neo4j"],
        "user_preferences": ["Prefers local execution"],
        "goals": ["Build a persistent LLM memory OS"],
        "skills": ["Full Stack Development", "FastAPI"],
        "recurring_topics": ["Vector Memory"],
        "important_decisions": ["Keep local architecture without cloud APIs"]
    }
    """

    parsed = analysis_service._parse_json_response(raw_llm_json, "fallback transcript")
    assert parsed["summary"] == "Discussed building MemOS companion app for Ollama Desktop using FastAPI and Next.js."
    assert "FastAPI" in parsed["technologies"]
    assert "MemOS" in parsed["projects"]
    assert len(parsed["entities"]) == 1

def test_analyze_chat_execution():
    async def run_test():
        db = next(get_test_db())

        # Create dummy user
        user = User(email="test@memos.ai", username="testuser", hashed_password="pw")
        db.add(user)
        db.commit()

        sample_messages = [
            {"role": "user", "content": "Hello! How are you doing today?"},
            {"role": "assistant", "content": "Hello! I am doing great. How can I help you?"},
            {"role": "user", "content": "I am working on the MemOS project. We are using FastAPI, Next.js, Qdrant and Neo4j. I prefer building local AI tools."}
        ]

        mock_llm_output = """
        {
            "summary": "User is building MemOS using FastAPI, Next.js, Qdrant, and Neo4j for local AI.",
            "facts": ["Building MemOS project", "Stack includes FastAPI, Next.js, Qdrant, and Neo4j"],
            "entities": [{"name": "FastAPI", "type": "Technology", "related_to": "MemOS", "relationship": "USES"}],
            "projects": ["MemOS"],
            "technologies": ["FastAPI", "Next.js", "Qdrant", "Neo4j"],
            "user_preferences": ["Prefers building local AI tools"],
            "goals": ["Develop MemOS companion app"],
            "skills": ["Python", "FastAPI", "Next.js"],
            "recurring_topics": ["Local AI architecture"],
            "important_decisions": ["All components must remain 100% local"]
        }
        """

        with patch("app.services.ollama_service.ollama_service.generate_chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.ollama_service.ollama_service.generate_embedding", new_callable=AsyncMock) as mock_embed, \
             patch("app.services.qdrant_service.qdrant_service.upsert_memory_vector") as mock_qdrant, \
             patch("app.services.graph_service.graph_service.add_fact") as mock_neo4j:
            
            mock_chat.return_value = mock_llm_output
            mock_embed.return_value = [0.1] * 768

            result = await analysis_service.analyze_chat(
                db=db,
                user_id=user.id,
                messages_input=sample_messages
            )

            assert result["summary"] != ""
            assert "MemOS" in result["projects"]
            assert "FastAPI" in result["technologies"]
            assert len(result["memories_created"]) > 0

            # Check DB UserProfile auto-update
            profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            assert profile is not None
            assert "MemOS" in profile.current_projects
            assert "FastAPI" in profile.technologies

    asyncio.run(run_test())

