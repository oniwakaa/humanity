from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Entry(Base):
    __tablename__ = "entries"

    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(Text, nullable=False)
    feature_type = Column(String, nullable=False, index=True) # e.g., 'free_diary', 'your_story', 'daily_questions_answ'
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata for vector store linkage or extra context
    meta = Column(JSON, default=dict)

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
