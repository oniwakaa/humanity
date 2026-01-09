from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Local SQLite database
# Use env var for persistence in packaged app
import os
data_dir = os.getenv("HUMANITY_DATA_DIR", ".")
os.makedirs(data_dir, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(data_dir, 'humanity.db')}"

# Create engine
# check_same_thread=False is needed for SQLite with FastAPI multi-threading
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Creates tables if they don't exist."""
    from api import models
    Base.metadata.create_all(bind=engine)
