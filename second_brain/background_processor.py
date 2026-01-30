"""Second Brain background processor - integrates with orchestrator queues.

Production-ready implementation with:
- LRU caching with TTL for context retrieval
- Structured observability (no PII)
- Graceful degradation and restart behavior
- Context quality guardrails
"""

import asyncio
import concurrent.futures
import threading
import atexit
import time
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
import json

from api.database import SessionLocal
from connectors.ollama import OllamaClient
from second_brain import SecondBrainService
from second_brain.ollama_adapter import OllamaAsyncAdapter
from utils.telemetry import get_logger

logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

CACHE_MAXSIZE = 100
CACHE_TTL_SECONDS = 300
CONTEXT_TIMEOUT_SECONDS = 8  # Reduced from 10 for faster feedback
BACKOFF_INITIAL_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 60.0
BACKOFF_MULTIPLIER = 2.0
RESTART_DELAY_SECONDS = 5.0
MINIMUM_CONTEXT_ENTRIES = 1
MAX_SUMMARY_TOKENS = 100  # For enforcing token budget


# =============================================================================
# LRU CACHE WITH TTL
# =============================================================================

class ContextCache:
    """Thread-safe LRU cache with TTL for context retrieval results."""
    
    def __init__(self, maxsize: int = CACHE_MAXSIZE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache: Dict[str, tuple] = {}  # key -> (value, timestamp)
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._access_times: Dict[str, float] = {}  # For LRU eviction
    
    def _make_key(self, query_text: str, token_budget: int) -> str:
        """Create cache key from query text and token budget."""
        key_content = f"{query_text}:{token_budget}"
        return hashlib.sha256(key_content.encode()).hexdigest()[:32]
    
    def get(self, query_text: str, token_budget: int) -> Optional[str]:
        """Get cached value if present and not expired."""
        key = self._make_key(query_text, token_budget)
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._access_times[key] = time.time()
                    return value
                # Expired - remove it
                del self._cache[key]
                del self._access_times[key]
            return None
    
    def set(self, query_text: str, token_budget: int, value: str) -> None:
        """Set cache value with LRU eviction if at capacity."""
        key = self._make_key(query_text, token_budget)
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._maxsize and key not in self._cache:
                oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
                del self._cache[oldest_key]
                del self._access_times[oldest_key]
            
            self._cache[key] = (value, time.time())
            self._access_times[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def size(self) -> int:
        """Return current cache size."""
        with self._lock:
            return len(self._cache)


# =============================================================================
# METRICS (NO PII)
# =============================================================================

class SecondBrainMetrics:
    """Structured metrics tracking for observability. No PII stored."""
    
    def __init__(self):
        self.success = 0
        self.empty_context = 0
        self.timeout = 0
        self.exception = 0
        self.cache_hit = 0
        self.cache_miss = 0
        self.fallback_used = 0
        self._lock = threading.Lock()
    
    def record(self, outcome: str, duration_ms: float, items_count: int = 0, 
               query_hash: Optional[str] = None, cache_hit: bool = False) -> None:
        """Record metrics and log structured event (no user content)."""
        with self._lock:
            if outcome == "success":
                self.success += 1
            elif outcome == "empty_context":
                self.empty_context += 1
            elif outcome == "timeout":
                self.timeout += 1
            elif outcome == "exception":
                self.exception += 1
            
            if cache_hit:
                self.cache_hit += 1
            else:
                self.cache_miss += 1
        
        # Structured logging - only IDs, metrics, no PII
        log_data = {
            "duration_ms": round(duration_ms, 2),
            "items_count": items_count,
            "outcome": outcome,
            "cache_hit": cache_hit
        }
        if query_hash:
            log_data["query_hash"] = query_hash
        
        if outcome in ("timeout", "exception"):
            logger.warning(f"second_brain_{outcome}", extra=log_data)
        else:
            logger.info(f"second_brain_{outcome}", extra=log_data)
    
    def record_fallback(self) -> None:
        """Record when fallback context (last entries) is used."""
        with self._lock:
            self.fallback_used += 1
        logger.info("second_brain_fallback_used", extra={"reason": "empty_retrieval"})
    
    def get_stats(self) -> Dict[str, int]:
        """Get current metrics snapshot."""
        with self._lock:
            return {
                "success": self.success,
                "empty_context": self.empty_context,
                "timeout": self.timeout,
                "exception": self.exception,
                "cache_hit": self.cache_hit,
                "cache_miss": self.cache_miss,
                "fallback_used": self.fallback_used,
                "cache_size": 0  # Will be populated by caller if needed
            }


# Global metrics instance
_metrics = SecondBrainMetrics()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _is_in_async_context() -> bool:
    """Check if we're currently running inside an async event loop."""
    try:
        loop = asyncio.get_running_loop()
        return loop is not None
    except RuntimeError:
        return False


def _hash_query(query_text: str) -> str:
    """Create a short hash of query text for logging (no PII)."""
    return hashlib.sha256(query_text.encode()).hexdigest()[:12]


# =============================================================================
# TASK DEFINITION
# =============================================================================

class SecondBrainTask:
    """Represents a Second Brain processing task for the queue."""

    def __init__(self, item_id: str, content: str, item_type: str = "note"):
        self.item_id = item_id
        self.content = content
        self.item_type = item_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "second_brain",
            "item_id": self.item_id,
            "content": self.content,
            "item_type": self.item_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["SecondBrainTask"]:
        if data.get("type") != "second_brain":
            return None
        return cls(
            item_id=data["item_id"],
            content=data["content"],
            item_type=data.get("item_type", "note")
        )


# =============================================================================
# BACKGROUND WORKER
# =============================================================================

class SecondBrainWorker:
    """
    Background worker for Second Brain processing.
    Processes items from the job queue independently.
    """

    def __init__(self, ollama_client: OllamaClient, embed_model: str, chat_model: str):
        self.ollama = ollama_client
        self.embed_model = embed_model
        self.chat_model = chat_model
        self._running = False

    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single Second Brain job."""
        task = SecondBrainTask.from_dict(job_data)
        if not task:
            return {"error": "Invalid job data"}

        db = SessionLocal()
        try:
            service = SecondBrainService(
                db=db,
                ollama=self.ollama,
                embed_model=self.embed_model,
                chat_model=self.chat_model
            )

            result = await service.process_new_item(
                item_id=task.item_id,
                content=task.content,
                item_type=task.item_type
            )

            logger.info(f"Second Brain Worker: processed {task.item_id} - {result['tags_created']} tags, {result['links_created']} links")
            return result

        except Exception as e:
            logger.error(f"Second Brain Worker failed for {task.item_id}: {e}")
            return {"error": str(e), "item_id": task.item_id}

        finally:
            db.close()

    async def run_batch(self, jobs: list) -> list:
        """Process multiple jobs sequentially (for simplicity)."""
        results = []
        for job in jobs:
            result = await self.process_job(job)
            results.append(result)
            # Brief pause between jobs to not overwhelm local resources
            await asyncio.sleep(0.1)
        return results


# =============================================================================
# CONTEXT INJECTOR (Production-ready)
# =============================================================================

class SecondBrainContextInjector:
    """
    Injects Second Brain context into AI prompts.
    Non-blocking: uses cached links, falls back gracefully.
    
    Production features:
    - LRU cache with TTL for context retrieval
    - Structured metrics (no PII)
    - Exponential backoff restart for background loop
    - Context quality guardrails (fallback if empty)
    - Proper atexit cleanup
    - Thread-safe future handling
    
    Thread-safe async/sync boundary:
    - Maintains a background thread with its own event loop
    - get_context_sync() schedules work on the background loop
    - Never creates nested event loops
    """

    def __init__(self, ollama_client: OllamaClient, embed_model: str):
        self.ollama = ollama_client
        self.embed_model = embed_model
        self._cache = ContextCache()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._restart_count = 0
        self._backoff_seconds = BACKOFF_INITIAL_SECONDS
        
        # Register atexit handler
        atexit.register(self.shutdown)
        
        # Start background loop
        self._start_background_loop()

    def _start_background_loop(self) -> None:
        """Start a daemon thread with a dedicated event loop and restart support."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            while not self._shutdown_event.is_set():
                try:
                    self._loop.run_forever()
                except Exception as e:
                    logger.error(f"Background loop crashed: {e}")
                
                # If shutdown not requested, attempt restart with backoff
                if not self._shutdown_event.is_set():
                    logger.warning(f"Background loop stopped unexpectedly, restarting in {self._backoff_seconds}s")
                    time.sleep(self._backoff_seconds)
                    self._backoff_seconds = min(
                        self._backoff_seconds * BACKOFF_MULTIPLIER, 
                        BACKOFF_MAX_SECONDS
                    )
                    self._restart_count += 1
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                
        self._thread = threading.Thread(target=run_loop, daemon=True, name="SecondBrainContextLoop")
        self._thread.start()
        logger.debug("Second Brain context background loop started")

    def shutdown(self) -> None:
        """Clean up resources: stop background loop and executor."""
        with self._lock:
            self._shutdown_event.set()
            
            if self._loop and self._loop.is_running():
                # Schedule loop stop from within the loop
                self._loop.call_soon_threadsafe(self._loop.stop)
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            
            self._executor.shutdown(wait=False)
            self._cache.clear()
            
            logger.debug("Second Brain context injector shutdown complete")

    def _get_fallback_context(self, current_item_id: Optional[str], count: int = 3) -> Dict[str, Any]:
        """Get fallback context: last N entries by created_at."""
        db = SessionLocal()
        try:
            from api.models import Entry
            
            query = db.query(Entry).order_by(Entry.created_at.desc())
            if current_item_id:
                query = query.filter(Entry.id != current_item_id)
            
            entries = query.limit(count).all()
            
            if not entries:
                return {"summary": "", "items": []}
            
            # Build simple summary
            summaries = []
            for entry in entries:
                preview = entry.text[:200] if entry.text else ""
                summaries.append(f"[{entry.feature_type}] {preview}")
            
            summary = "\n".join(summaries)
            return {
                "summary": summary,
                "items": [
                    {
                        "item_id": e.id,
                        "item_type": e.feature_type,
                        "preview": e.text[:150] if e.text else ""
                    }
                    for e in entries
                ]
            }
        except Exception as e:
            logger.warning(f"Fallback context retrieval failed: {e}")
            return {"summary": "", "items": []}
        finally:
            db.close()

    async def get_context_for_prompt(
        self,
        query_text: str,
        current_item_id: Optional[str] = None,
        token_budget: int = 500,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Get Second Brain context formatted for prompt injection.
        
        Features:
        - Caching with TTL
        - Fallback to recent entries if empty result
        - Token budget enforcement
        - Structured metrics (no PII)
        """
        start_time = time.time()
        query_hash = _hash_query(query_text)
        
        # Check cache first
        cached = self._cache.get(query_text, token_budget)
        if cached is not None:
            duration_ms = (time.time() - start_time) * 1000
            _metrics.record("success", duration_ms, items_count=1, query_hash=query_hash, cache_hit=True)
            return {"summary": cached, "cached": True}
        
        db = SessionLocal()
        try:
            from second_brain import SecondBrainService

            service = SecondBrainService(
                db=db,
                ollama=self.ollama,
                embed_model=self.embed_model
            )

            context = await service.get_context_for_query(
                query_text=query_text,
                current_item_id=current_item_id,
                top_k=top_k,
                token_budget=token_budget
            )
            
            summary = context.get("summary", "")
            items_count = len(context.get("items", []))
            
            # Context quality guardrail: if empty, try fallback
            if not summary or items_count < MINIMUM_CONTEXT_ENTRIES:
                _metrics.record_fallback()
                fallback = self._get_fallback_context(current_item_id, count=3)
                if fallback["summary"]:
                    summary = fallback["summary"]
                    items_count = len(fallback["items"])
            
            # Enforce token budget in summary (rough approximation: 4 chars ≈ 1 token)
            max_chars = token_budget * 4
            if len(summary) > max_chars:
                summary = summary[:max_chars].rsplit('.', 1)[0] + '.'
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Cache the result
            self._cache.set(query_text, token_budget, summary)
            
            # Record metrics
            outcome = "success" if summary else "empty_context"
            _metrics.record(outcome, duration_ms, items_count=items_count, query_hash=query_hash)
            
            return {
                "summary": summary,
                "items": context.get("items", []),
                "retrieval_ms": round(duration_ms, 2),
                "total_ms": round(duration_ms, 2),
                "cached": False
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            _metrics.record("timeout", duration_ms, query_hash=query_hash)
            logger.warning("Second Brain context retrieval timed out")
            return {"summary": "", "error": "timeout", "retrieval_ms": round(duration_ms, 2)}

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            _metrics.record("exception", duration_ms, query_hash=query_hash)
            logger.warning(f"Second Brain context retrieval failed (graceful fallback): {e}")
            return {"summary": "", "error": str(e), "retrieval_ms": round(duration_ms, 2)}

        finally:
            db.close()

    def get_context_sync(
        self,
        query_text: str,
        current_item_id: Optional[str] = None,
        token_budget: int = 500,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper around get_context_for_prompt.
        
        Production features:
        - Reduced timeout (8 seconds)
        - Thread-safe future handling with proper cleanup
        - Automatic restart of background loop if needed
        - Structured error returns
        
        Thread-safe implementation:
        - If already in async context, uses async version directly
        - Otherwise schedules work on background event loop
        - Never creates nested event loops
        
        Returns dict with summary, timing metrics, and optional error field.
        """
        start_time = time.time()
        query_hash = _hash_query(query_text)
        future = None
        
        try:
            # Check if we're already in an async context
            if _is_in_async_context():
                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        self.get_context_for_prompt(
                            query_text=query_text,
                            current_item_id=current_item_id,
                            token_budget=token_budget,
                            top_k=top_k
                        ),
                        loop
                    )
                    result = future.result(timeout=CONTEXT_TIMEOUT_SECONDS)
                    total_ms = (time.time() - start_time) * 1000
                    result["total_ms"] = round(total_ms, 2)
                    return result
                except RuntimeError:
                    pass
            
            # Schedule on background loop via thread pool executor
            with self._lock:
                if not self._loop or not self._loop.is_running():
                    logger.warning("Second Brain background loop not running, attempting restart")
                    self._start_background_loop()
                
                future = asyncio.run_coroutine_threadsafe(
                    self.get_context_for_prompt(
                        query_text=query_text,
                        current_item_id=current_item_id,
                        token_budget=token_budget,
                        top_k=top_k
                    ),
                    self._loop
                )
                
                result = future.result(timeout=CONTEXT_TIMEOUT_SECONDS)
                total_ms = (time.time() - start_time) * 1000
                result["total_ms"] = round(total_ms, 2)
                
                # Reset backoff on success
                self._backoff_seconds = BACKOFF_INITIAL_SECONDS
                
                return result
                
        except concurrent.futures.TimeoutError:
            total_ms = (time.time() - start_time) * 1000
            _metrics.record("timeout", total_ms, query_hash=query_hash)
            logger.warning("Second Brain get_context_sync timed out (graceful fallback)")
            
            # Cancel the future if it exists
            if future and not future.done():
                future.cancel()
            
            return {
                "summary": "",
                "error": "timeout",
                "total_ms": round(total_ms, 2)
            }
            
        except Exception as e:
            total_ms = (time.time() - start_time) * 1000
            _metrics.record("exception", total_ms, query_hash=query_hash)
            logger.warning(f"Second Brain get_context_sync failed (graceful fallback): {e}")
            
            # Cancel the future if it exists and is not done
            if future and not future.done():
                future.cancel()
            
            return {
                "summary": "",
                "error": str(e),
                "total_ms": round(total_ms, 2)
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics and cache stats."""
        stats = _metrics.get_stats()
        stats["cache_size"] = self._cache.size()
        stats["restart_count"] = self._restart_count
        return stats


# =============================================================================
# QUEUE INTEGRATION
# =============================================================================

def queue_second_brain_task(
    queue,
    item_id: str,
    content: str,
    item_type: str = "note"
):
    """
    Queue a Second Brain task using the existing JobQueue system.
    Call this from orchestrator when new items are created.
    """
    task = SecondBrainTask(item_id, content, item_type)
    queue.push(task.to_dict())
    logger.debug(f"Queued Second Brain task for {item_id}")


# =============================================================================
# MIGRATION UTILITIES
# =============================================================================

def migrate_existing_entries(
    ollama_client: OllamaClient,
    embed_model: str,
    chat_model: str,
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    One-time migration: Process all existing entries through Second Brain.
    Process in batches to avoid overwhelming the system.
    Returns stats about the migration.
    """
    from api.models import Entry, ItemTag

    db = SessionLocal()
    try:
        # Find entries without tags
        untagged_entries = (
            db.query(Entry)
            .outerjoin(ItemTag, ItemTag.item_id == Entry.id)
            .filter(ItemTag.item_id.is_(None))
            .all()
        )

        total = len(untagged_entries)
        if total == 0:
            return {"processed": 0, "message": "No untagged entries found"}

        logger.info(f"Second Brain migration: found {total} untagged entries")

        # Process in batches
        processed = 0
        errors = 0

        async def process_batch(batch):
            nonlocal processed, errors
            worker = SecondBrainWorker(ollama_client, embed_model, chat_model)

            jobs = [
                SecondBrainTask(e.id, e.text, e.feature_type).to_dict()
                for e in batch
            ]

            results = await worker.run_batch(jobs)

            for result in results:
                if "error" in result:
                    errors += 1
                else:
                    processed += 1

        # Run batches (synchronous wrapper)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for i in range(0, len(untagged_entries), batch_size):
            batch = untagged_entries[i:i + batch_size]
            loop.run_until_complete(process_batch(batch))
            logger.info(f"Second Brain migration: processed {min(i + batch_size, total)}/{total}")

        loop.close()

        return {
            "processed": processed,
            "errors": errors,
            "total": total
        }

    finally:
        db.close()
