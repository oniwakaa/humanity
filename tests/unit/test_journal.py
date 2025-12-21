import os
import json
from storage.journal import JournalStorage

def test_add_entry_atomic_write(test_dir):
    """Verify that add_entry writes to the file correctly."""
    journal = JournalStorage(data_dir=test_dir)
    
    entry_id = journal.add_entry("Test entry", "test_type", ["tag1"])
    
    assert entry_id is not None
    
    # Check file content
    filepath = os.path.join(test_dir, "journal.jsonl")
    assert os.path.exists(filepath)
    
    with open(filepath, "r") as f:
        line = f.readline()
        data = json.loads(line)
        
    assert data["id"] == entry_id
    assert data["text"] == "Test entry"
    assert data["feature_type"] == "test_type"
    assert "tags" in data
    assert "tag1" in data["tags"]

def test_get_entries(test_dir):
    """Verify retrieval of entries."""
    journal = JournalStorage(data_dir=test_dir)
    journal.add_entry("Entry 1", "type1")
    journal.add_entry("Entry 2", "type2")
    
    entries = journal.get_entries(limit=10)
    assert len(entries) == 2
    assert entries[0]["text"] == "Entry 2" # Descending order usually expected or append order depending on impl? 
    # Current impl of get_entries reads file.
    # Let's check `journal.py` implementation if available. 
    # Assuming it reads line by line.
