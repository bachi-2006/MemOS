import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("MemoryModel", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


class MemoryModel(Base):
    """
    Canonical Memory Model stored in PostgreSQL metadata database
    """
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    
    # Research & Lifecycle scores
    importance_score = Column(Float, default=1.0)
    confidence_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    source = Column(String, default="chat") # e.g. 'chat', 'ollama_hook', 'manual'
    tags = Column(JSON, default=list)
    entities = Column(JSON, default=list)
    relationships = Column(JSON, default=list)
    status = Column(String, default="active") # 'active', 'archived', 'forgotten'
    
    # Feature 6 & 7 & 2 Extensions
    collection = Column(String, default="General") # e.g., Projects, Coding, Research, Personal, Work, etc.
    project = Column(String, nullable=True) # e.g., MemOS
    is_pinned = Column(Boolean, default=False)

    user = relationship("User", back_populates="memories")


class UserProfile(Base):
    """
    User Profile metadata automatically generated and continuously updated by MemOS
    """
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    preferred_languages = Column(JSON, default=list)
    preferred_frameworks = Column(JSON, default=list)
    current_projects = Column(JSON, default=list)
    interests = Column(JSON, default=list)
    skills = Column(JSON, default=list)
    technologies = Column(JSON, default=list)
    writing_style = Column(Text, nullable=True, default="Concise, technical, direct")
    learning_goals = Column(JSON, default=list)
    preferred_model = Column(String, nullable=True, default="qwen3.5:9b")
    recent_focus = Column(JSON, default=list)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class AnalysisHistory(Base):
    """
    Tracks chat analysis sessions and memory optimization runs
    """
    __tablename__ = "analysis_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    chat_id = Column(String, nullable=True)
    summary = Column(Text, nullable=False)
    entities_extracted = Column(JSON, default=list)
    facts_extracted = Column(JSON, default=list)
    duplicates_removed = Column(Integer, default=0)
    graph_nodes_added = Column(Integer, default=0)
    vectors_indexed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

