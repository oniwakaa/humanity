from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from api.database import SessionLocal
from api.models import Entry
import json

class DBManager:
    def __init__(self):
        # We don't hold a long-lived session here typically, 
        # but for compatibility with the existing simple Orchestrator pattern, 
        # we can create one on the fly or accept one.
        # For now, we will create fresh sessions for operations to avoid threading issues 
        # given the simple Architecture.
        pass

    def add_entry(self, text: str, feature_type: str, tags: List[str] = None) -> str:
        """Adds a new entry to the database."""
        db: Session = SessionLocal()
        try:
            new_entry = Entry(
                text=text,
                feature_type=feature_type,
                tags=tags or []
            )
            db.add(new_entry)
            db.commit()
            db.refresh(new_entry)
            return new_entry.id
        finally:
            db.close()

    def get_entries(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves entries, ordered by creation date desc."""
        db: Session = SessionLocal()
        try:
            entries = db.query(Entry).order_by(Entry.created_at.desc()).offset(offset).limit(limit).all()
            return [self._to_dict(e) for e in entries]
        finally:
            db.close()

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        db: Session = SessionLocal()
        try:
            entry = db.query(Entry).filter(Entry.id == entry_id).first()
            if entry:
                return self._to_dict(entry)
            return None
        finally:
            db.close()

    def _to_dict(self, entry: Entry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "text": entry.text,
            "feature_type": entry.feature_type,
            "tags": entry.tags,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            # Backwards compatibility fields for Orchestratror
            "timestamp": entry.created_at.timestamp() if entry.created_at else 0
        }
