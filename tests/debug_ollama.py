import sys
import os
sys.path.append(os.getcwd())

from connectors.ollama import OllamaClient
from settings.manager import SettingsManager

def debug_ollama():
    try:
        settings = SettingsManager().get_config()
        print(f"Configured URL: {settings.ollama.base_url}")
        
        client = OllamaClient(settings.ollama.base_url)
        
        print("Attempting check_health()...")
        # Access internal request directly to see error
        try:
            client._handle_request("GET", "/")
            print("check_health OK")
        except Exception as e:
            print(f"check_health FAILED with: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        print("\nAttempting list_models()...")
        try:
            models = client.list_models()
            print(f"Models found: {models}")
        except Exception as e:
            print(f"list_models FAILED with: {e}")

    except Exception as e:
        print(f"Global Fail: {e}")

if __name__ == "__main__":
    debug_ollama()
