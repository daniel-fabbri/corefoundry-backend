"""Database models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from corefoundry.app.db.connection import Base
from corefoundry.app.db.auth_models import AuthUser


class Agent(Base):
    """Agent model for storing agent configurations."""
    
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    model_name = Column(String(255), nullable=False, default="llama2")
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("AuthUser", foreign_keys=[user_id])
    messages = relationship("Message", back_populates="agent", cascade="all, delete-orphan")
    memory_entries = relationship("Memory", back_populates="agent", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', model='{self.model_name}')>"


class Message(Base):
    """Message model for storing chat history."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=True, index=True)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="messages")
    thread = relationship("Thread", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, agent_id={self.agent_id}, role='{self.role}')>"


class Memory(Base):
    """Memory model for storing agent memory."""
    
    __tablename__ = "memory"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    memory_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="memory_entries")
    
    def __repr__(self):
        return f"<Memory(id={self.id}, agent_id={self.agent_id}, key='{self.key}')>"


class KnowledgeChunk(Base):
    """Knowledge chunk model for storing knowledge base."""
    
    __tablename__ = "knowledge_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    source = Column(String(500), nullable=True)
    chunk_metadata = Column(JSON, nullable=True)
    embedding = Column(Text, nullable=True)  # Store as JSON string for now
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeChunk(id={self.id}, source='{self.source}', agent_id={self.agent_id})>"


class ChatUser(Base):
    """Chat user model for thread ownership (deprecated - use AuthUser)."""

    __tablename__ = "chat_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Note: threads relationship removed - now using AuthUser for threads

    def __repr__(self):
        return f"<ChatUser(id={self.id}, name='{self.name}')>"


class Thread(Base):
    """Thread model for conversation isolation by user and agent."""

    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Thread")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="threads")
    user = relationship("AuthUser", foreign_keys=[user_id])
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Thread(id={self.id}, agent_id={self.agent_id}, user_id={self.user_id}, title='{self.title}')>"
