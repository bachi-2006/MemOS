from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Canonical Memory Schema
class MemorySchema(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    content: str
    importance_score: float = 1.0
    confidence_score: float = 1.0
    access_count: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    source: str = "chat"
    tags: List[str] = []
    entities: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []
    status: str = "active"
    collection: str = "General"
    project: Optional[str] = None
    is_pinned: bool = False

    model_config = ConfigDict(from_attributes=True)

# Chat & Ollama Schemas
class ChatRequest(BaseModel):
    chat_id: Optional[str] = None
    prompt: str
    model: Optional[str] = "qwen3.5:9b"
    system_context: Optional[str] = None
    personalized: bool = True
    active_project: Optional[str] = None


class MemoryShareHook(BaseModel):
    """Schema for Ollama app local memory sharing button trigger"""
    user_id: Optional[str] = None
    content: str
    tags: List[str] = []
    source: str = "ollama_app_hook"

class ChatMessageItem(BaseModel):
    role: str
    content: str

class AnalyzeChatRequest(BaseModel):
    chat_id: Optional[str] = None
    messages: Optional[List[ChatMessageItem]] = None

class AnalyzeChatResponse(BaseModel):
    summary: str
    facts: List[str] = []
    entities: List[Dict[str, Any]] = []
    projects: List[str] = []
    technologies: List[str] = []
    user_preferences: List[str] = []
    goals: List[str] = []
    skills: List[str] = []
    recurring_topics: List[str] = []
    important_decisions: List[str] = []
    memories_created: List[Dict[str, Any]] = []
    duplicates_removed: int = 0
    graph_nodes_created: int = 0
    conflicts_detected: List[Dict[str, Any]] = []

class UserProfileSchema(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    preferred_languages: List[str] = []
    preferred_frameworks: List[str] = []
    current_projects: List[str] = []
    interests: List[str] = []
    skills: List[str] = []
    technologies: List[str] = []
    writing_style: Optional[str] = "Concise, technical, direct"
    learning_goals: List[str] = []
    preferred_model: Optional[str] = "qwen3.5:9b"
    recent_focus: List[str] = []
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

