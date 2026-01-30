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
        # Process embedding jobs (legacy pipeline)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.orchestrator.run_embedding_worker)

        # Process Second Brain generation jobs (async-friendly)
        # These require LLM calls for tagging and linking
        await self._process_second_brain_jobs()

    async def _process_second_brain_jobs(self):
        """Process pending Second Brain tasks from the queue."""
        from second_brain.background_processor import SecondBrainTask

        job = self.orchestrator.embed_queue.peek()
        if not job or job.get("type") != "second_brain":
            return

        # Pop the job immediately to avoid reprocessing
        self.orchestrator.embed_queue.pop()

        try:
            result = await self.orchestrator.second_brain_worker.process_job(job)
            if "error" in result:
                print(f"Second Brain job failed: {result['error']}")
        except Exception as e:
            print(f"Second Brain job error: {e}")
        
    def stop(self):
        self.running = False
