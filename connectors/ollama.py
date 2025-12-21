import httpx
from typing import List, Dict, Any, Optional
from utils.errors import (
    OllamaError, OllamaUnreachableError, OllamaTimeoutError, 
    OllamaModelNotFoundError, OllamaBadResponseError
)

class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _handle_request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            response = httpx.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise OllamaUnreachableError(f"Could not connect to Ollama at {self.base_url}")
        except httpx.TimeoutException:
            raise OllamaTimeoutError(f"Request to {url} timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # potentially model not found or endpoint not found
                # For chat/generate, usually it returns logic errors in body, but 404 on model pull
                # We interpret generic 404 as BadResponse unless specific context known
                 raise OllamaBadResponseError(f"HTTP 404: {e}")
            raise OllamaBadResponseError(f"HTTP {e.response.status_code}: {e}")
        except Exception as e:
            raise OllamaError(f"Unexpected error: {e}")

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
            self._handle_request("GET", "/") # basic root check usually works or returns 200 "Ollama is running"
            return True
        except:
             return False
