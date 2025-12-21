import pytest
from unittest.mock import MagicMock
from storage.memory import MemoryLayer

def test_memory_search_wraps_qdrant():
    """Verify search calls Qdrant Client correctly."""
    # Mock Qdrant Client
    mem = MemoryLayer("http://mock", "mock_coll")
    mem.client = MagicMock()
    
    # Mock return
    mock_hit = MagicMock()
    mock_hit.payload = {"text": "hit"}
    mem.client.search.return_value = [mock_hit]
    
    # Act
    hits = mem.search([0.1]*10, limit=3, filters={"type": "test"})
    
    # Assert
    assert len(hits) == 1
    assert hits[0]["text"] == "hit"
    mem.client.search.assert_called_once()
    
    # Verify filter construction args
    call_args = mem.client.search.call_args
    assert "query_filter" in call_args.kwargs
    assert call_args.kwargs["query_filter"] is not None
