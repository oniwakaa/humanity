import sys
import os
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from storage.memory import MemoryLayer

def test_chroma_persistence():
    print("--- Testing ChromaDB Persistence ---")
    
    test_dir = "./data/test_chroma"
    if Path(test_dir).exists():
        shutil.rmtree(test_dir)
        
    # 1. Initialize
    print("Initializing MemoryLayer...")
    mem = MemoryLayer(persistence_path=test_dir, collection_name="test_entries")
    
    if not mem.check_health():
        print("❌ Chroma Heartbeat Failed")
        return False
    print("✔ Chroma Initialized")
    
    # 2. Insert Data
    print("Inserting chunk...")
    chunks = [{"chunk_id": "c1", "text": "This is a test entry about AI.", "entry_id": "e1"}]
    # Fake embedding (dim 1024)
    embedding = [0.1] * 1024
    
    try:
        mem.upsert_chunks(chunks, [embedding])
        print("✔ Upsert successful")
    except Exception as e:
        print(f"❌ Upsert failed: {e}")
        return False
        
    # 3. Search
    print("Searching...")
    try:
        results = mem.search(query_vector=embedding, limit=1)
        if len(results) == 1 and results[0]["chunk_id"] == "c1":
            print("✔ Search successful (Found correct chunk)")
        else:
            print(f"❌ Search failed or incorrect results: {results}")
            return False
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False

    # 4. Clean up
    shutil.rmtree(test_dir)
    print("✔ Cleanup successful")
    return True

if __name__ == "__main__":
    try:
        import chromadb
        success = test_chroma_persistence()
        if success:
            print("\n✅ Verification PASSED")
        else:
            print("\n❌ Verification FAILED")
            sys.exit(1)
    except ImportError:
        print("❌ chromadb not installed. Run: pip install chromadb")
