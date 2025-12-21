import pytest
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

import shutil
import tempfile
from settings.manager import SettingsManager
from settings.config_model import AppConfig, OllamaConfig, QdrantConfig, STTConfig

@pytest.fixture(scope="function")
def test_dir():
    """Creates a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_settings(test_dir):
    """Returns a SettingsManager configured with a temp storage path."""
    # Create the manager but we'll override the config load logic or just rely on the fact 
    # that we can init classes with specific configs if we structure them right.
    # But Orchestrator loads from SettingsManager().get_config() which usually reads config.json.
    # For integration tests, we might want to patch SettingsManager.
    
    # Let's create a temporary config.json in the test_dir
    config_path = os.path.join(test_dir, "config.json")
    
    # We need to make sure the app uses this. 
    # Since SettingsManager defaults to looking at relative 'config.json', 
    # we might need to monkeypatch or pass config explicitly.
    # Engine takes settings_manager as init arg. Good.
    
    class MockSettingsManager(SettingsManager):
        def get_config(self) -> AppConfig:
            return AppConfig(
                ollama=OllamaConfig(base_url="http://localhost:11434", num_ctx=2048),
                qdrant=QdrantConfig(url="http://localhost:6333", collection_name="test_journal"),
                stt=STTConfig(model_path="mock_path"),
                storage_path=test_dir
            )
            
    return MockSettingsManager()

@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from api.server import app
    return TestClient(app)
