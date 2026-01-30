# Second Brain: Ollama Client Adapter
# Adapts the sync OllamaClient to async interface used by Second Brain

import asyncio
from typing import List, Dict, Any, Optional

class OllamaAsyncAdapter:
    """
    Wraps the synchronous OllamaClient to provide async methods.
    This prevents blocking the event loop during LLM calls.
    """

    def __init__(self, ollama_client):
        self.client = ollama_client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Async wrapper for chat-based generation."""

        def _call():
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            return self.client.chat(
                model=model or self.client.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )

        # Run blocking call in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _call)

        # Extract response text
        content = result.get("message", {}).get("content", "")
        return {"response": content}

    async def embeddings(self, model: str, prompt: str) -> Dict[str, Any]:
        """Async wrapper for embedding generation."""

        def _call():
            embedding = self.client.embed(model, prompt)
            return {"embedding": embedding}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Async wrapper for chat completion."""

        def _call():
            return self.client.chat(model, messages, options=options)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)


# Provide alias for backward compatibility
OllamaConnector = OllamaAsyncAdapter
