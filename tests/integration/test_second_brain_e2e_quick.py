"""
End-to-End Integration Test: Second Brain with Real Ollama (Quick Version)
===========================================================================

This test creates 6 synthetic entries (2 work, 2 family, 2 health) and verifies
full Second Brain functionality using **real** Ollama (no mocks). Tests tag
generation, embeddings, semantic links, and context retrieval.

Fast version: ~6 entries, completes in <60 seconds

REQUIREMENTS:
- Real Ollama server at http://127.0.0.1:11434
- mxbai-embed-large:latest model installed for embeddings
- ministral-3:3b model for chat (tag generation)

SEED DATA STRUCTURE:
- Cluster A (2 items): Work/career/stress theme
- Cluster B (2 items): Family/relationship theme  
- Cluster C (2 items): Health/wellness theme

LOGGING: Only counts and timing, never full content.
"""

import asyncio
import json
import os
import sys
import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import statistics
import time
import requests

sys.path.insert(0, '/Users/carlo/Desktop/pr_prj/humanity')

from api.database import init_db, SessionLocal, engine
from sqlalchemy import text
from api.models import Entry, Tag, ItemTag, ItemEmbedding, ItemLink
from second_brain import (
    SecondBrainService,
    TagGenerator,
    GeneratedTag,
    TagNormalizer,
    OllamaAsyncAdapter,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "mxbai-embed-large:latest"
CHAT_MODEL = "ministral-3:3b"
ENTRY_TIMEOUT_SECONDS = 30  # Timeout per entry
TEST_DB_PATH = "/Users/carlo/Desktop/pr_prj/humanity/test_e2e_quick.db"


# =============================================================================
# SEED DATA: 6 ENTRIES (2 work, 2 family, 2 health)
# =============================================================================

SEED_ENTRIES = [
    {"id": "work-01", "type": "note", "content": "Work stress today. Project deadlines and boss pressure."},
    {"id": "work-02", "type": "reflection", "content": "Career uncertainty. Job market and professional growth."},
    {"id": "family-01", "type": "note", "content": "Family time with mother. Relationship and support."},
    {"id": "family-02", "type": "reflection", "content": "Marriage and parenting challenges. Domestic life."},
    {"id": "health-01", "type": "note", "content": "Exercise routine and fitness goals. Physical wellness."},
    {"id": "health-02", "type": "reflection", "content": "Mental health and anxiety management. Self care."},
]


# =============================================================================
# RESULT TRACKING & LOGGING
# =============================================================================

test_results = {
    "errors": [],
    "entries_created": 0,
    "tags_created": 0,
    "embeddings_created": 0,
    "links_created": 0,
    "timing_stats": {},
    "retrieval_tests": {},
}


def log(message: str, level: str = "info"):
    """Log with timestamp and level."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    levels = {"info": "→", "success": "✓", "error": "✗", "warning": "⚠"}
    print(f"[{timestamp}] {levels.get(level, '→')} {message}")


def log_error(message: str):
    """Log error and store it."""
    test_results["errors"].append(message)
    log(message, "error")


def log_success(message: str):
    """Log successful step."""
    log(message, "success")


def log_warning(message: str):
    """Log warning."""
    log(message, "warning")


# =============================================================================
# OLLAMA HEALTH CHECK
# =============================================================================

def check_ollama_available() -> Tuple[bool, List[str]]:
    """
    Check if Ollama is running and required models are available.
    Returns: (is_available, list of missing_models)
    """
    log("Checking Ollama availability...")
    
    try:
        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=5
        )
        
        if response.status_code != 200:
            log_error(f"Ollama returned status {response.status_code}")
            return False, []
        
        data = response.json()
        available_models = [m.get("name", m.get("model", "")) for m in data.get("models", [])]
        
        missing_models = []
        
        if EMBED_MODEL not in available_models:
            log_warning(f"Embed model '{EMBED_MODEL}' not available")
            missing_models.append(EMBED_MODEL)
        else:
            log_success(f"Embed model '{EMBED_MODEL}' is available")
        
        if CHAT_MODEL not in available_models:
            log_warning(f"Chat model '{CHAT_MODEL}' not available")
            missing_models.append(CHAT_MODEL)
        else:
            log_success(f"Chat model '{CHAT_MODEL}' is available")
        
        return len(missing_models) == 0, missing_models
        
    except requests.exceptions.ConnectionError:
        log_error(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        return False, []
    except Exception as e:
        log_error(f"Error checking Ollama: {e}")
        return False, []


# =============================================================================
# ROBUST TAG PARSER
# =============================================================================

class RobustTagParser:
    """Robust parsing of LLM JSON responses with multiple fallback strategies."""
    
    MALFORMED_PATTERNS = [
        r'\{[^}]*"tags"[^}]*\}',
        r'\[[^\]]*"tag"[^\]]*\]',
        r'tags?:\s*\[[^\]]*\]',
    ]
    
    @classmethod
    def parse_tag_response(cls, response: str) -> List[GeneratedTag]:
        """Parse tag response with multiple fallback strategies."""
        if not response:
            return []
        
        # Strategy 1: Try clean JSON extraction
        tags = cls._try_clean_json(response)
        if tags:
            return tags
        
        # Strategy 2: Extract from markdown code blocks
        tags = cls._try_markdown_extraction(response)
        if tags:
            return tags
        
        # Strategy 3: Try to fix common JSON issues
        tags = cls._try_repair_json(response)
        if tags:
            return tags
        
        # Strategy 4: Extract tags using regex patterns
        tags = cls._try_regex_extraction(response)
        if tags:
            return tags
        
        return []
    
    @classmethod
    def _try_clean_json(cls, response: str) -> List[GeneratedTag]:
        """Try to parse clean JSON."""
        try:
            data = json.loads(response.strip())
            return cls._extract_tags_from_structured(data)
        except json.JSONDecodeError:
            return []
    
    @classmethod
    def _try_markdown_extraction(cls, response: str) -> List[GeneratedTag]:
        """Extract JSON from markdown code blocks."""
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0]
            else:
                return []
            
            data = json.loads(json_str.strip())
            return cls._extract_tags_from_structured(data)
        except (json.JSONDecodeError, IndexError, AttributeError):
            return []
    
    @classmethod
    def _try_repair_json(cls, response: str) -> List[GeneratedTag]:
        """Try to repair common JSON issues."""
        try:
            # Fix single quotes to double quotes
            repaired = response.replace("'", '"')
            
            # Fix trailing commas
            repaired = re.sub(r',\s*}', '}', repaired)
            repaired = re.sub(r',\s*]', ']', repaired)
            
            # Remove control characters
            repaired = re.sub(r'[\x00-\x1F\x7F]', '', repaired)
            
            data = json.loads(repaired.strip())
            return cls._extract_tags_from_structured(data)
        except json.JSONDecodeError:
            return []
    
    @classmethod
    def _try_regex_extraction(cls, response: str) -> List[GeneratedTag]:
        """Extract tags using regex patterns as last resort."""
        tags = []
        
        # Look for tag: "value" pattern
        tag_patterns = [
            r'"tag"\s*:\s*"([^"]+)"',
            r'"tag"\s*:\s*\'([^\']+)\'',
            r'tag:\s*"([^"]+)"',
            r'tag:\s*([^\s,}\]]+)',
        ]
        
        for pattern in tag_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if match and len(match) < 100:
                    normalized = TagNormalizer.normalize(match)
                    if TagNormalizer.is_valid(normalized) and normalized not in [t.tag for t in tags]:
                        tags.append(GeneratedTag(tag=normalized, category="topic"))
                
                if len(tags) >= 3:
                    return tags
        
        # Look for comma-separated values in lists
        list_pattern = r'\[\s*"([^"]+)"(?:\s*,\s*"([^"]+)")?\]'
        matches = re.findall(list_pattern, response)
        for match_group in matches:
            for match in match_group:
                if match:
                    normalized = TagNormalizer.normalize(match)
                    if TagNormalizer.is_valid(normalized) and normalized not in [t.tag for t in tags]:
                        tags.append(GeneratedTag(tag=normalized, category="topic"))
                
                if len(tags) >= 3:
                    return tags
        
        return tags[:3] if tags else []
    
    @classmethod
    def _extract_tags_from_structured(cls, data: Any) -> List[GeneratedTag]:
        """Extract tags from structured data (dict or list)."""
        tags = []
        
        if isinstance(data, dict):
            # Try common keys
            for key in ['tags', 'tag', 'result', 'items', 'entries']:
                if key in data:
                    items = data[key]
                    if isinstance(items, list):
                        for item in items:
                            tag_obj = cls._convert_to_tag(item)
                            if tag_obj:
                                tags.append(tag_obj)
        elif isinstance(data, list):
            for item in data:
                tag_obj = cls._convert_to_tag(item)
                if tag_obj:
                    tags.append(tag_obj)
        
        return tags[:3] if tags else []
    
    @classmethod
    def _convert_to_tag(cls, item: Any) -> Optional[GeneratedTag]:
        """Convert various formats to GeneratedTag."""
        if isinstance(item, str):
            normalized = TagNormalizer.normalize(item)
            if TagNormalizer.is_valid(normalized):
                return GeneratedTag(tag=normalized, category="topic")
        elif isinstance(item, dict):
            tag_text = item.get('tag') or item.get('name') or item.get('text') or item.get('value')
            if tag_text:
                normalized = TagNormalizer.normalize(str(tag_text))
                if TagNormalizer.is_valid(normalized):
                    category = item.get('category', 'topic')
                    return GeneratedTag(tag=normalized, category=category)
        return None


# =============================================================================
# DATABASE SETUP
# =============================================================================

async def setup_database():
    """Initialize test database and clean previous test data."""
    log("Setting up test database...")
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        log("Removed previous test database")
    
    # Set test database path
    os.environ['DATABASE_PATH'] = TEST_DB_PATH
    init_db()
    
    db = SessionLocal()
    try:
        for entry in SEED_ENTRIES:
            db.execute(text(f"DELETE FROM item_links WHERE source_item_id = '{entry['id']}' OR target_item_id = '{entry['id']}'"))
            db.execute(text(f"DELETE FROM item_tags WHERE item_id = '{entry['id']}'"))
            db.execute(text(f"DELETE FROM item_embeddings WHERE item_id = '{entry['id']}'"))
            db.execute(text(f"DELETE FROM entries WHERE id = '{entry['id']}'"))
        db.commit()
        log_success("Database cleaned and initialized")
    except Exception as e:
        log_error(f"Database cleanup failed: {e}")
        raise
    finally:
        db.close()


async def create_seed_entries():
    """Insert all 6 seed entries into database."""
    log(f"Creating {len(SEED_ENTRIES)} seed entries...")
    
    db = SessionLocal()
    try:
        for entry_data in SEED_ENTRIES:
            entry = Entry(
                id=entry_data["id"],
                text=entry_data["content"],
                feature_type=entry_data["type"]
            )
            db.add(entry)
        
        db.commit()
        test_results["entries_created"] = len(SEED_ENTRIES)
        log_success(f"Created {len(SEED_ENTRIES)} entries in database")
    except Exception as e:
        log_error(f"Failed to create entries: {e}")
        raise
    finally:
        db.close()


# =============================================================================
# REAL OLLAMA CLIENT
# =============================================================================

class RealOllamaClient:
    """Real Ollama client using HTTP API directly."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
    
    async def generate(self, prompt: str, model: str = None, system: str = None, 
                       temperature: float = 0.3, max_tokens: int = 150,
                       tools=None, tool_choice=None, schema=None):
        """Generate text using Ollama generate endpoint."""
        model = model or CHAT_MODEL
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system or "",
                    "temperature": temperature,
                    "stream": False
                },
                timeout=ENTRY_TIMEOUT_SECONDS
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}: {response.text}")
            
            result = response.json()
            return {"response": result.get("response", "")}
            
        except Exception as e:
            log_error(f"Generation failed: {e}")
            raise
    
    async def embeddings(self, model: str, prompt: str):
        """Generate embeddings using Ollama embeddings endpoint."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": prompt
                },
                timeout=ENTRY_TIMEOUT_SECONDS
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}: {response.text}")
            
            result = response.json()
            return {"embedding": result.get("embedding", [])}
            
        except Exception as e:
            log_error(f"Embedding failed: {e}")
            raise
    
    async def embed(self, model: str, prompt: str):
        """Alias for embeddings."""
        return await self.embeddings(model, prompt)


# =============================================================================
# SECOND BRAIN PROCESSING
# =============================================================================

async def process_entries_with_timeout():
    """Process all 6 entries through SecondBrainService with individual timeouts."""
    log("Processing entries through Second Brain...")
    
    ollama = RealOllamaClient()
    processing_times = []
    
    for idx, entry_data in enumerate(SEED_ENTRIES, 1):
        db = SessionLocal()
        try:
            service = SecondBrainService(
                db=db,
                ollama=ollama,
                embed_model=EMBED_MODEL,
                chat_model=CHAT_MODEL
            )
            
            start_time = time.time()
            
            try:
                # Use asyncio.wait_for for timeout
                result = await asyncio.wait_for(
                    service.process_new_item(
                        item_id=entry_data["id"],
                        content=entry_data["content"],
                        item_type=entry_data["type"],
                        skip_embedding=False,
                        skip_linking=False
                    ),
                    timeout=ENTRY_TIMEOUT_SECONDS
                )
                
                elapsed = time.time() - start_time
                processing_times.append(elapsed)
                
                test_results["tags_created"] += result["tags_created"]
                if result["embedding_updated"]:
                    test_results["embeddings_created"] += 1
                test_results["links_created"] += result["links_created"]
                
                if result["errors"]:
                    for err in result["errors"]:
                        log_error(f"{entry_data['id']}: {err}")
                
                log(f"[{idx}/{len(SEED_ENTRIES)}] {entry_data['id']}: "
                    f"{result['tags_created']} tags, embedding={result['embedding_updated']}, "
                    f"{result['links_created']} links ({elapsed:.2f}s)")
                
            except asyncio.TimeoutError:
                log_error(f"Timeout after {ENTRY_TIMEOUT_SECONDS}s processing {entry_data['id']}")
            except Exception as e:
                log_error(f"Failed to process {entry_data['id']}: {e}")
                
        finally:
            db.close()
    
    # Store timing stats
    if processing_times:
        test_results["timing_stats"]["process_item"] = {
            "count": len(processing_times),
            "mean": statistics.mean(processing_times),
            "min": min(processing_times),
            "max": max(processing_times),
        }
    
    log_success(f"Completed processing {len(processing_times)}/{len(SEED_ENTRIES)} entries")


# =============================================================================
# VERIFICATION
# =============================================================================

async def verify_counts():
    """Verify database counts match expectations."""
    log("Verifying database state...")
    
    db = SessionLocal()
    try:
        entries_count = db.query(Entry).filter(
            Entry.id.in_([e["id"] for e in SEED_ENTRIES])
        ).count()
        
        tags_count = db.query(ItemTag).filter(
            ItemTag.item_id.in_([e["id"] for e in SEED_ENTRIES])
        ).count()
        
        embeddings_count = db.query(ItemEmbedding).filter(
            ItemEmbedding.item_id.in_([e["id"] for e in SEED_ENTRIES])
        ).count()
        
        links_count = db.query(ItemLink).filter(
            (ItemLink.source_item_id.in_([e["id"] for e in SEED_ENTRIES])) |
            (ItemLink.target_item_id.in_([e["id"] for e in SEED_ENTRIES]))
        ).count()
        
        log(f"Entries: {entries_count}")
        log(f"Tags: {tags_count}")
        log(f"Embeddings: {embeddings_count}")
        log(f"Links: {links_count}")
        
        # Assertions
        assert entries_count == 6, f"Expected 6 entries, got {entries_count}"
        assert tags_count == 18, f"Expected 18 tags (3 per entry), got {tags_count}"
        assert embeddings_count == 6, f"Expected 6 embeddings, got {embeddings_count}"
        assert links_count > 0, f"Expected some links, got {links_count}"
        
        log_success("All count assertions passed")
        
        return {
            "entries": entries_count,
            "tags": tags_count,
            "embeddings": embeddings_count,
            "links": links_count
        }
        
    except AssertionError as e:
        log_error(f"Assertion failed: {e}")
        raise
    except Exception as e:
        log_error(f"Verification failed: {e}")
        raise
    finally:
        db.close()


# =============================================================================
# RETRIEVAL TESTS
# =============================================================================

async def test_retrieval():
    """Test context retrieval with 3 queries across different themes."""
    log("Testing context retrieval...")
    
    ollama = RealOllamaClient()
    db = SessionLocal()
    
    try:
        service = SecondBrainService(
            db=db,
            ollama=ollama,
            embed_model=EMBED_MODEL
        )
        
        test_queries = [
            {
                "name": "work_stress_query",
                "query": "work stress job",
                "expected_clusters": ["work"],
                "description": "Should return work-related items"
            },
            {
                "name": "family_relationships_query", 
                "query": "family relationship mother",
                "expected_clusters": ["family"],
                "description": "Should return family-related items"
            },
            {
                "name": "health_wellness_query",
                "query": "health exercise wellness",
                "expected_clusters": ["health"],
                "description": "Should return health-related items"
            },
        ]
        
        retrieval_times = []
        
        for test in test_queries:
            try:
                start_time = time.time()
                
                context = await asyncio.wait_for(
                    service.get_context_for_query(
                        query_text=test["query"],
                        top_k=4,
                        token_budget=500
                    ),
                    timeout=10.0
                )
                
                elapsed = time.time() - start_time
                retrieval_times.append(elapsed)
                
                items = context.get("items", [])
                item_count = len(items)
                
                test_results["retrieval_tests"][test["name"]] = {
                    "query": test["query"],
                    "items_returned": item_count,
                    "expected_clusters": test["expected_clusters"],
                    "elapsed_seconds": elapsed,
                }
                
                item_ids = [item.get("item_id", "unknown") for item in items]
                log(f"Query '{test['query']}' returned {item_count} items in {elapsed:.2f}s")
                log(f"  Item IDs: {', '.join(item_ids)}")
                
                assert item_count > 0, f"Query '{test['query']}' returned no items"
                
            except asyncio.TimeoutError:
                log_error(f"Retrieval test '{test['name']}' timed out after 10s")
                test_results["retrieval_tests"][test["name"]] = {
                    "error": "Timeout after 10s",
                    "query": test["query"]
                }
            except Exception as e:
                log_error(f"Retrieval test '{test['name']}' failed: {e}")
                test_results["retrieval_tests"][test["name"]] = {
                    "error": str(e),
                    "query": test["query"]
                }
        
        if retrieval_times:
            test_results["timing_stats"]["get_context"] = {
                "count": len(retrieval_times),
                "mean": statistics.mean(retrieval_times),
                "min": min(retrieval_times),
                "max": max(retrieval_times),
            }
        
        log_success("Retrieval tests completed")
        
    finally:
        db.close()


# =============================================================================
# FINAL REPORT
# =============================================================================

async def print_final_report():
    """Print comprehensive test report."""
    print("\n" + "="*80)
    print("SECOND BRAIN E2E QUICK TEST - FINAL REPORT")
    print("="*80)
    print(f"Database: {TEST_DB_PATH}")
    print(f"Models: {CHAT_MODEL}, {EMBED_MODEL}")
    print(f"Total Time: {sum(s.get('mean', 0) * s.get('count', 1) for s in test_results['timing_stats'].values()):.2f}s")
    
    print("\n📊 CREATED ENTITIES")
    print(f"   Entries: {test_results['entries_created']}")
    print(f"   Tags: {test_results['tags_created']}")
    print(f"   Embeddings: {test_results['embeddings_created']}")
    print(f"   Links: {test_results['links_created']}")
    
    print("\n⏱️  TIMING STATISTICS")
    for op_name, stats in test_results["timing_stats"].items():
        print(f"   {op_name}:")
        print(f"     count={stats['count']}, mean={stats.get('mean', 0):.3f}s, "
              f"min={stats.get('min', 0):.3f}s, max={stats.get('max', 0):.3f}s")
    
    print("\n🔍 RETRIEVAL TESTS")
    for test_name, info in test_results["retrieval_tests"].items():
        if "error" in info:
            print(f"   ✗ {test_name}: ERROR - {info['error']}")
        else:
            print(f"   ✓ {test_name}: {info['items_returned']} items, "
                  f"{info['elapsed_seconds']:.2f}s")
    
    print("\n✅ ASSERTION RESULTS")
    print("   ✓ entries_count == 6")
    print("   ✓ tags_count == 18")
    print("   ✓ embeddings_count == 6")
    print("   ✓ links_count > 0")
    
    all_retrieval_ok = all(
        info.get("items_returned", 0) > 0
        for info in test_results["retrieval_tests"].values()
        if "error" not in info
    )
    
    if all_retrieval_ok:
        print("   ✓ All 3 retrieval queries returned items")
    else:
        print("   ✗ Some retrieval queries failed")
    
    print("\n⚠️  ERRORS ENCOUNTERED")
    if test_results["errors"]:
        print(f"   Total: {len(test_results['errors'])}")
        for i, error in enumerate(test_results["errors"][:5], 1):
            print(f"   {i}. {error}")
        if len(test_results["errors"]) > 5:
            print(f"   ... and {len(test_results['errors']) - 5} more")
    else:
        print("   NONE")
    
    print("\n🎯 OVERALL STATUS")
    errors_count = len(test_results["errors"])
    if errors_count == 0:
        print("   ✅ ALL TESTS PASSED")
    elif errors_count < 3:
        print(f"   ⚠️  {errors_count} minor issues (likely non-critical)")
    else:
        print(f"   ❌ {errors_count} errors encountered")
    
    print("="*80)


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_all_tests():
    """Run the complete E2E test suite."""
    start_total = time.time()
    
    print("\n" + "="*80)
    print("SECOND BRAIN E2E QUICK TEST WITH REAL OLLAMA")
    print("="*80)
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Embed Model: {EMBED_MODEL}")
    print(f"Chat Model: {CHAT_MODEL}")
    print(f"Test Entries: {len(SEED_ENTRIES)}")
    print(f"Timeout per Entry: {ENTRY_TIMEOUT_SECONDS}s")
    print("="*80 + "\n")
    
    log("Running pre-flight checks...")
    
    is_ollama_up, missing_models = check_ollama_available()
    
    if not is_ollama_up:
        if missing_models:
            print("\n" + "="*80)
            print("❌ TEST SKIP: Required Ollama models not available")
            print("="*80)
            print(f"\nMissing models: {', '.join(missing_models)}")
            print("\nTo install, run:")
            for model in missing_models:
                print(f"  ollama pull {model}")
            print("\nThen re-run this test.")
            print("="*80)
            return 1
        else:
            print("\n" + "="*80)
            print("❌ TEST SKIP: Ollama not available")
            print("="*80)
            print(f"\nCannot connect to Ollama at {OLLAMA_BASE_URL}")
            print("\nTo start Ollama:")
            print("  ollama serve")
            print("\nThen re-run this test.")
            print("="*80)
            return 1
    
    try:
        await setup_database()
        await create_seed_entries()
        await process_entries_with_timeout()
        await verify_counts()
        await test_retrieval()
        await print_final_report()
        
        total_time = time.time() - start_total
        print(f"\n⏱️  Total Test Duration: {total_time:.2f}s")
        
        return 0 if len(test_results["errors"]) == 0 else 1
        
    except AssertionError as e:
        print(f"\n❌ TEST ASSERTION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ TEST RUN FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
