import sys
import os
import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from api.models import Entry, DailyCycle
from settings.manager import SettingsManager
from storage.memory import MemoryLayer
from connectors.ollama import OllamaClient

# Setup DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./humanity.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def verify_db():
    print("--- Verifying SQLite Persistence ---")
    session = SessionLocal()
    try:
        entries = session.query(Entry).order_by(Entry.created_at.desc()).limit(5).all()
        print(f"Total Entries Found: {session.query(Entry).count()}")
        for e in entries:
            print(f"[{e.created_at}] Type: {e.feature_type} | ID: {e.id}")
            print(f"Preview: {e.text[:50]}...")
            
        cycles = session.query(DailyCycle).order_by(DailyCycle.date.desc()).all()
        print(f"\nTotal Daily Cycles: {len(cycles)}")
    finally:
        session.close()

def verify_rag():
    print("\n--- Verifying Vector Retrieval (RAG) ---")
    settings = SettingsManager().get_config()
    
    # Check Qdrant
    try:
        mem = MemoryLayer(settings.qdrant.url, settings.qdrant.collection_name)
        if not mem.check_health():
            print("❌ Qdrant not reachable")
            return

        ollama = OllamaClient(settings.ollama.base_url)
        if not ollama.check_health():
             print("❌ Ollama not reachable")
             return
             
        # Embed query
        query_text = "reflection" 
        print(f"Querying for: '{query_text}'")
        vec = ollama.embed(settings.ollama.embed_model, query_text)
        
        results = mem.search(vec, limit=3)
        print(f"Found {len(results)} matches:")
        for res in results:
            print(f" - Score: {res.get('_score', 0):.4f} | Text: {res.get('text', '')[:60]}...")
            
    except Exception as e:
        print(f"RAG Error: {e}")

if __name__ == "__main__":
    verify_db()
    verify_rag()
