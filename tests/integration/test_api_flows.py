from fastapi.testclient import TestClient

def test_api_entry_create_flow(api_client, mock_settings):
    """Verify posting an entry works and returns ID."""
    
    # We rely on api_client fixture using the app which uses global `orchestrator`.
    # `orchestrator` uses `SettingsManager`. 
    # Since `conftest` setup `mock_settings`, we hope `orchestrator` picks it up?
    # Actually, `server.py` instantiates `SettingsManager()` globally at import time.
    # To mock it effectively, we might need to patch `api.server.settings_mgr` OR 
    # reload the module. 
    # For now, let's assumes `settings.manager.SettingsManager` reads from CWD or env.
    # A cleaner integration test would set env vars before import.
    
    response = api_client.post("/entry", json={"text": "Integration Test Entry", "tags": ["test"]})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["message"] == "Entry saved and queued for indexing."

def test_daily_generate_endpoint(api_client):
    """Test generating daily questions via API."""
    response = api_client.post("/daily/generate")
    if response.status_code == 200:
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) >= 6
    else:
        # It might fail if 500
        assert False, f"API Failed: {response.text}"
