import requests
import time

BASE_URL = "http://localhost:8000"

def test_diary_flow():
    print("--- 1. Testing Chat with RAG ---")
    # Simulate a chat message
    chat_payload = {
        "message": "I'm feeling a bit overwhelmed by the project deadlines.",
        "context": [] # First message
    }
    max_retries = 3
    for i in range(max_retries):
        try:
            res = requests.post(f"{BASE_URL}/chat", json=chat_payload)
            res.raise_for_status()
            print(f"AI Response: {res.json()['response']}")
            break
        except Exception as e:
            print(f"Chat Attempt {i+1} Failed: {e}")
            time.sleep(2)

    print("\n--- 2. Testing Diary Save ---")
    # Simulate finishing a session
    transcript = [
        {"role": "user", "content": "I'm feeling overwhelmed."},
        {"role": "assistant", "content": "That sounds tough. What specifically is causing the pressure?"},
        {"role": "user", "content": "Just the sheer volume of tasks."}
    ]
    save_payload = {"transcript": transcript}
    
    try:
        res = requests.post(f"{BASE_URL}/diary/save", json=save_payload)
        res.raise_for_status()
        entry_id = res.json()["id"]
        print(f"Saved Entry ID: {entry_id}")
    except Exception as e:
        print(f"Save Failed: {e}")
        return

if __name__ == "__main__":
    time.sleep(2) # Wait for server restart
    test_diary_flow()
