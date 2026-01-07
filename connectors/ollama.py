import httpx
from typing import List, Dict, Any, Optional
from utils.errors import (
    OllamaError, OllamaUnreachableError, OllamaTimeoutError, 
    OllamaModelNotFoundError, OllamaBadResponseError
)

class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        import threading
        self.lock = threading.Lock() # Serialize requests to prevent local GPU panic

    def _handle_request(self, method: str, endpoint: str, **kwargs) -> Any:
        import time
        url = f"{self.base_url}{endpoint}"
        max_retries = 3
        backoff = 2.0
        
        # Acquire lock to ensure only one request hits Ollama at a time
        with self.lock:
            for i in range(max_retries):
                try:
                    response = httpx.request(method, url, timeout=self.timeout, **kwargs)
                    response.raise_for_status()
                    return response.json()
                except httpx.ConnectError:
                    raise OllamaUnreachableError(f"Could not connect to Ollama at {self.base_url}")
                except httpx.TimeoutException:
                     # On timeout, maybe don't retry immediately inside lock if it takes 30s? 
                     # Actually if it times out, Ollama is likely stuck. 
                     # Better to fail fast or retry? 
                     # For now, treat timeout as failure to avoid 90s hang.
                    raise OllamaTimeoutError(f"Request to {url} timed out after {self.timeout}s")
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                         raise OllamaBadResponseError(f"HTTP 404: {e}")
                    
                    if e.response.status_code >= 500:
                        error_text = e.response.text
                        print(f"Ollama {e.response.status_code} Error: {error_text}. Retrying {i+1}/{max_retries}...")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                        
                    raise OllamaBadResponseError(f"HTTP {e.response.status_code}: {e}")
                except Exception as e:
                    raise OllamaError(f"Unexpected error: {e}")
            
            raise OllamaError(f"Failed after {max_retries} retries")

    def list_models(self) -> List[str]:
        """Returns a list of available model names."""
        try:
            data = self._handle_request("GET", "/api/tags")
            # Structure is usually {"models": [{"name": "llama3:latest", ...}]}
            models = [m["name"] for m in data.get("models", [])]
            return models
        except KeyError:
            raise OllamaBadResponseError("Unexpected format in /api/tags response")

    def embed(self, model: str, prompt: str) -> List[float]:
        """Generates embeddings for a single string."""
        payload = {
            "model": model,
            "prompt": prompt
        }
        try:
            data = self._handle_request("POST", "/api/embeddings", json=payload)
            return data["embedding"]
        except httpx.HTTPStatusError as e:
             if e.response.status_code == 404:
                 raise OllamaModelNotFoundError(f"Model '{model}' not encountered during embedding")
             raise
        except KeyError:
             raise OllamaBadResponseError("Missing 'embedding' in response")

    def chat(self, model: str, messages: List[Dict[str, str]], stream: bool = False, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Simple non-streaming chat completion."""
        if stream:
            raise NotImplementedError("Streaming not yet implemented in this client wrapper")
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        
        try:
            return self._handle_request("POST", "/api/chat", json=payload)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                 raise OllamaModelNotFoundError(f"Model '{model}' not found")
            raise

    def check_health(self) -> bool:
        """Quick check if reachable."""
        try:
            self._handle_request("GET", "/api/version") 
            return True
        except:
            return False

    def pull_model(self, model: str):
        """
        Pulls a model from the registry. Yields progress status dicts.
        """
        url = f"{self.base_url}/api/pull"
        payload = {"name": model, "stream": True}
        
        import json
        with httpx.stream("POST", url, json=payload, timeout=None) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    try:
                        yield json.loads(line)
                    except:
                        pass
