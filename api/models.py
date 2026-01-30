from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

# =============================================================================
# SECOND BRAIN: Tagging + Embeddings + Links
# =============================================================================

class Tag(Base):
    """Normalized tag storage for the Second Brain knowledge graph."""
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True, index=True)  # normalized lowercase tag
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item_tags = relationship("ItemTag", back_populates="tag", cascade="all, delete-orphan")


class ItemTag(Base):
    """Join table linking items (entries) to tags."""
    __tablename__ = "item_tags"

    item_id = Column(String, ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tag = relationship("Tag", back_populates="item_tags")
    entry = relationship("Entry", back_populates="item_tags")


class ItemEmbedding(Base):
    """Embeddings storage for semantic similarity links."""
    __tablename__ = "item_embeddings"

    id = Column(String, primary_key=True, default=generate_uuid)
    item_id = Column(String, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    embedding_json = Column(JSON, nullable=False)  # Store as JSON array for portability
    embedding_model = Column(String, nullable=False)  # e.g., "mxbai-embed-large:latest"
    embedding_dim = Column(Integer, nullable=False)  # e.g., 1024
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Composite index for fast model-based queries
    __table_args__ = (Index('idx_embedding_item_model', 'item_id', 'embedding_model'),)


class ItemLink(Base):
    """Knowledge graph links between items via tags or semantic similarity."""
    __tablename__ = "item_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_item_id = Column(String, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    target_item_id = Column(String, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    link_type = Column(String, nullable=False, index=True)  # 'tag_match' | 'semantic'
    weight = Column(Float, nullable=False)  # 0.0 to 1.0
    explanation = Column(String, nullable=True)  # Short context (max 200 chars)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Composite index for efficient graph traversal
    __table_args__ = (
        Index('idx_links_source_type', 'source_item_id', 'link_type'),
        Index('idx_links_target_type', 'target_item_id', 'link_type'),
    )

# =============================================================================
# CORE ENTRY MODEL (Extended for Second Brain)
# =============================================================================

class Entry(Base):
    __tablename__ = "entries"

    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(Text, nullable=False)
    feature_type = Column(String, nullable=False, index=True) # e.g., 'free_diary', 'your_story', 'daily_questions_answ', 'note', 'reflection', 'conversation'
    tags = Column(JSON, default=list)  # Legacy JSON tags (kept for backward compat)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Metadata for vector store linkage or extra context
    meta = Column(JSON, default=dict)

    # Second Brain relationships
    item_tags = relationship("ItemTag", back_populates="entry", cascade="all, delete-orphan")
    embedding = relationship("ItemEmbedding", uselist=False, back_populates="entry", cascade="all, delete-orphan")
    outgoing_links = relationship("ItemLink", foreign_keys="ItemLink.source_item_id", back_populates="source_entry", cascade="all, delete-orphan")
    incoming_links = relationship("ItemLink", foreign_keys="ItemLink.target_item_id", back_populates="target_entry", cascade="all, delete-orphan")


# Patch relationship back-references
Tag.item_tags = relationship("ItemTag", back_populates="tag", cascade="all, delete-orphan")
ItemEmbedding.entry = relationship("Entry", back_populates="embedding")
ItemLink.source_entry = relationship("Entry", foreign_keys="ItemLink.source_item_id", back_populates="outgoing_links")
ItemLink.target_entry = relationship("Entry", foreign_keys="ItemLink.target_item_id", back_populates="incoming_links")

    # Relationships could go here if we had a separate User table, 
    # but for Local-First V1 single-user, we might skip User table or just have a singleton.
    
class DailyCycle(Base):
    __tablename__ = "daily_cycles"
    
    id = Column(String, primary_key=True) # UUID provided by orchestrator
    date = Column(DateTime(timezone=True), server_default=func.now())
    questions = Column(JSON, nullable=False) # The set of questions generated
    answers = Column(JSON, nullable=True) # The answers submitted
    
    status = Column(String, default="pending") # pending, completed

class UserProfile(Base):
    __tablename__ = "user_profile"
    
    id = Column(Integer, primary_key=True, index=True) 
    # Singleton row usually id=1
    profile_json = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
