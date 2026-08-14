from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.session import get_db
from app.api.deps import get_current_user_optional
from app.models.models import User, UserProfile
from app.schemas.schemas import UserProfileSchema

router = APIRouter(prefix="/profile", tags=["User Profile & Auto-Learned Preferences"])

@router.get("/", response_model=UserProfileSchema)
def get_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Feature 3: Get User Profile.
    Returns automatically generated and continuously updated user profile metadata.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            preferred_languages=["Python", "TypeScript"],
            preferred_frameworks=["FastAPI", "Next.js"],
            current_projects=["MemOS"],
            interests=["Local AI", "Vector Memory", "Knowledge Graphs"],
            skills=["Full Stack Engineering", "AI Systems Architecture"],
            technologies=["Qdrant", "Neo4j", "Ollama", "PostgreSQL"],
            writing_style="Concise, technical, direct",
            learning_goals=["Build fully autonomous local agent OS"],
            preferred_model="qwen3.5:9b",
            recent_focus=["Local Context Injection", "Knowledge Graph Synapses"]
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.patch("/", response_model=UserProfileSchema)
def update_user_profile(
    payload: UserProfileSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Feature 3: Manually Update User Profile.
    Users can edit any field (languages, frameworks, projects, skills, style, goals, etc.).
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key not in ["id", "user_id", "updated_at"] and value is not None:
            setattr(profile, key, value)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile
