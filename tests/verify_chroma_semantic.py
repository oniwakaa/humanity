import sys
import os
import shutil
import time
from pathlib import Path
from typing import List

# Add project root to path
sys.path.append(os.getcwd())

from storage.memory import MemoryLayer
from connectors.ollama import OllamaClient
from settings.config_model import OllamaConfig

TEST_DB_PATH = "./data/test_chroma_semantic"
COLLECTION_NAME = "semantic_test"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "mxbai-embed-large:latest"

def setup_clean_db():
    if Path(TEST_DB_PATH).exists():
        shutil.rmtree(TEST_DB_PATH)
    return MemoryLayer(persistence_path=TEST_DB_PATH, collection_name=COLLECTION_NAME)

def get_ollama_client():
    client = OllamaClient(base_url=OLLAMA_URL)
    if not client.check_health():
        print(f"❌ Ollama not reachable at {OLLAMA_URL}")
        sys.exit(1)
    return client

def test_semantic_accuracy():
    print("\n--- Phase 1: Semantic Accuracy Test ---")
    
    mem = setup_clean_db()
    ollama = get_ollama_client()
    
    # 1. Generate Test Data
    data_entries = [
        {"id": "e1", "theme": "Work Stress", "text": "I feel completely overwhelmed by the deadlines. My boss is demanding too much and I can't sleep."},
        {"id": "e2", "theme": "Family Joy", "text": "Had a wonderful dinner with my mom today. She brought old photos and we laughed for hours."},
        {"id": "e3", "theme": "Health Anxiety", "text": "My knee has been hurting for weeks. I'm worried it might be something serious preventing me from running."},
        {"id": "e4", "theme": "Coding", "text": "Debugging this Python script is tricky, but I think the vector database integration is finally working."}
    ]
    
    print(f"Inserting {len(data_entries)} entries...")
    
    chunks = []
    embeddings = []
    
    for entry in data_entries:
        # Generate embedding
        try:
            vec = ollama.embed(EMBED_MODEL, entry["text"])
            embeddings.append(vec)
            
            chunks.append({
                "chunk_id": f"c_{entry['id']}",
                "entry_id": entry['id'],
                "text": entry['text'],
                "theme": entry['theme']
            })
            print(f"  Embedded: {entry['theme']}")
        except Exception as e:
            print(f"❌ Embedding failed for {entry['theme']}: {e}")
            sys.exit(1)
            
    # Upsert
    mem.upsert_chunks(chunks, embeddings)
    print("✔ Data Upserted")
    
    # 2. Query Test
    test_queries = [
        ("I feel overwhelmed by my job.", "Work Stress"),
        ("My mom is visiting.", "Family Joy"),
        ("My leg hurts when I run.", "Health Anxiety")
    ]
    
    for query_text, expected_theme in test_queries:
        print(f"\nQuerying: '{query_text}'")
        q_vec = ollama.embed(EMBED_MODEL, query_text)
        results = mem.search(q_vec, limit=1)
        
        if not results:
            print("❌ No results found!")
            return False
            
        top_hit = results[0]
        score = top_hit.get('_score', 0)
        found_theme = top_hit.get('theme', 'Unknown')
        
        print(f"  -> Top Hit: '{found_theme}' (Score: {score:.4f})")
        
        if found_theme == expected_theme:
            print("  ✔ Match Confirmed")
        else:
            print(f"  ❌ Mismatch! Expected '{expected_theme}', got '{found_theme}'")
            return False
            
    return True

def test_persistence():
    print("\n--- Phase 2: Persistence Check ---")
    
    # Simulate "Restart" by re-initializing MemoryLayer pointing to SAME path
    print("Simulating Process Restart (Re-initializing MemoryLayer)...")
    mem_reloaded = MemoryLayer(persistence_path=TEST_DB_PATH, collection_name=COLLECTION_NAME)
    
    ollama = get_ollama_client()
    
    # Probe Data
    probe_query = "Debugging code"
    print(f"Querying for '{probe_query}' in reloaded DB...")
    
    q_vec = ollama.embed(EMBED_MODEL, probe_query)
    results = mem_reloaded.search(q_vec, limit=1)
    
    if results and results[0].get("theme") == "Coding":
        print("✔ Persistence Verified: Found 'Coding' entry after reload.")
        return True
    else:
        print(f"❌ Persistence Failed: Could not find entry. Results: {results}")
        return False

def cleanup():
    if Path(TEST_DB_PATH).exists():
        shutil.rmtree(TEST_DB_PATH)
    print("\n✔ Cleanup complete")

if __name__ == "__main__":
    try:
        if test_semantic_accuracy() and test_persistence():
            print("\n✅ ALL TESTS PASSED: Semantics & Persistence OK")
            cleanup()
            sys.exit(0)
        else:
            print("\n❌ TESTS FAILED")
            cleanup()
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        cleanup()
        sys.exit(1)
