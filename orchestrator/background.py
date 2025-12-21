import asyncio
import time
from typing import Optional
from settings.manager import SettingsManager
from orchestrator.engine import Orchestrator
from orchestrator.queues import JobQueue

class BackgroundWorker:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.running = False
        self.poll_interval = 2.0  # Seconds
        self.error_backoff = 2.0

    async def run(self):
        """Main loop."""
        self.running = True
        print("Starting Background Worker...")
        while self.running:
            try:
                # Naively process one job at a time
                await self.process_next_job()
                # If queue empty, sleep
                # Optimally we check if job was processed, if not sleep.
                # For MVP, simple sleep is fine.
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print(f"Background Worker Error: {e}")
                await asyncio.sleep(self.error_backoff)

    async def process_next_job(self):
        # We need to access the queue. 
        # The orchestrator exposes `run_embedding_worker` which is synchronous in current impl.
        # We wrap it or call it.
        # Current `run_embedding_worker` in engine.py:
        # 1. PEEKS
        # 2. Embeds
        # 3. POPS
        
        # We can just call it. But it blocks.
        # Ideally we make it async or run in executor.
        
        # Check health first?
        # If Ollama is down, we shouldn't pop/fail, but maybe peek/check.
        # engine.py logic has simple try/catch.
        
        # Let's run it in an executor to avoid blocking the async event loop if needed,
        # but since we are just doing HTTP requests, we could make `OllamaClient` async.
        # For now, MVP:
        
        # We'll just call the method. 
        # Note: `run_embedding_worker` prints errors and doesn't pop if failed (except for specific logic).
        # We need to verify `engine.py` logic again.
        
        # If `run_embedding_worker` raises, we catch in `run`.
        # If it returns, we assume success or handled failure.
        
        # To make this non-blocking for FastAPI:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.orchestrator.run_embedding_worker)
        
    def stop(self):
        self.running = False
