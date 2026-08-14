import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import Base
from app.models.models import User, UserProfile
from app.api.profile import get_user_profile, update_user_profile
from app.schemas.schemas import UserProfileSchema

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

def test_user_profile_crud():
    db = next(get_test_db())

    user = User(email="profile_test@memos.ai", username="prof_user", hashed_password="pw")
    db.add(user)
    db.commit()

    # 1. Get profile (auto initializes default)
    profile = get_user_profile(db=db, current_user=user)
    assert profile is not None
    assert "Python" in profile.preferred_languages
    assert "MemOS" in profile.current_projects

    # 2. Update profile manually
    update_payload = UserProfileSchema(
        preferred_languages=["Python", "TypeScript", "Rust"],
        preferred_frameworks=["FastAPI", "Next.js", "PyTorch"],
        current_projects=["MemOS", "Ollama Desktop"],
        writing_style="Direct, clean, production-ready code",
        preferred_model="qwen3.5:9b"
    )

    updated = update_user_profile(payload=update_payload, db=db, current_user=user)
    assert "Rust" in updated.preferred_languages
    assert "PyTorch" in updated.preferred_frameworks
    assert "Ollama Desktop" in updated.current_projects
    assert updated.writing_style == "Direct, clean, production-ready code"
