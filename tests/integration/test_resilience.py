from orchestrator.engine import Orchestrator
from unittest.mock import MagicMock

def test_daily_gen_resilience_to_ollama_failure(mock_settings):
    """Verify generator falls back if Ollama raises error."""
    orch = Orchestrator(mock_settings)
    
    # Mock Ollama failure
    orch.ollama.chat = MagicMock(side_effect=Exception("Connection Refused"))
    
    # Act
    result = orch.generate_daily_questions()
    
    # Assert
    assert result["questions"] is not None
    assert len(result["questions"]) >= 6
    # Should use fallback
    assert result["questions"][0]["id"].startswith("fb")
