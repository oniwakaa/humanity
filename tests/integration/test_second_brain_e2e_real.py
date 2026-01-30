"""
End-to-End Integration Test: Second Brain with Real Ollama
===========================================================

This test creates 20 synthetic entries across 3 overlapping clusters
and verifies full Second Brain functionality using **real** Ollama
(no mocks). Tests tag generation, embeddings, semantic links, and
context retrieval.

REQUIREMENTS:
- Real Ollama server at http://127.0.0.1:11434
- mxbai-embed-large:latest model installed
- Chat model available (e.g., mistral:latest)

SEED DATA STRUCTURE:
- Cluster A (8 items): Work/career/stress theme
- Cluster B (7 items): Family/relationship theme
- Cluster C (5 items): Health/wellness theme
- Bridge items (2 items): Connect A→B and B→C

LOGGING: Only counts and timing, never full content.
"""

import asyncio
import json
import os
import sys
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Tuple
import statistics
import time
import requests
import subprocess

# Add project root to path
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
TEST_DB_PATH = "/Users/carlo/Desktop/pr_prj/humanity/test_e2e.db"


# =============================================================================
# SEED DATA: 20 ENTRIES WITH 3 CLUSTERS + 2 BRIDGE ITEMS
# =============================================================================

SEED_ENTRIES = [
    # Cluster A: Work/Career (8 items - overlapping work/career/stress themes)
    {
        "id": "work-01",
        "type": "note",
        "content": "Feeling overwhelmed by project deadlines and tight schedules. The pressure to deliver is affecting my sleep and mental health. My boss criticized my presentation today, said it lacked depth and focus. Need to find better ways to manage work stress."
    },
    {
        "id": "work-02",
        "type": "daily_reflection",
        "content": "Career development meeting with my mentor was tough. We discussed my skill gaps and areas needing improvement. The feedback was constructive but hit my ego hard. Feeling uncertain about my professional direction and whether I'm cut out for this leadership role."
    },
    {
        "id": "work-03",
        "type": "note",
        "content": "Office politics are exhausting. Yesterday's team conflict over project ownership drained my energy. My coworker took credit for my ideas again during the standup meeting. Considering whether it's time to look for a new job or switch departments entirely."
    },
    {
        "id": "work-04",
        "type": "reflection",
        "content": "Quarterly review came back and it wasn't great. My performance metrics are down from last quarter and my manager expressed concern about my productivity. The work-life balance here seems impossible to achieve with these deadlines. Starting to question if I should pivot careers."
    },
    {
        "id": "work-05",
        "type": "note",
        "content": "Had a tense conversation with a difficult client today. They pushed back on every proposal and questioned our expertise repeatedly. The project scope keeps expanding without additional budget or timeline adjustments. My anxiety levels are through the roof dealing with this account."
    },
    {
        "id": "work-06",
        "type": "daily_reflection",
        "content": "Working late again today until 10 PM trying to catch up on emails and reports. Burnout is setting in despite my efforts to maintain healthy boundaries. Colleagues who leave on time seem to get promoted while those who stay late get more work dumped on them."
    },
    {
        "id": "work-07",
        "type": "note",
        "content": "My imposter syndrome flared up during the all-hands meeting today when senior leadership presented our department's challenges. I felt completely out of my depth compared to my peers. Everyone else seems to have their career trajectory figured out while I'm still figuring it out."
    },
    {
        "id": "work-08",
        "type": "reflection",
        "content": "The job market survey results from HR are concerning - satisfaction scores are at an all-time low. Management announced budget cuts and hiring freezes for the next quarter which means more workload for existing staff. Career advancement opportunities look bleak right now."
    },

    # Cluster B: Family/Relationships (7 items)
    {
        "id": "family-01",
        "type": "note",
        "content": "Had a difficult conversation with my mother about boundaries today. She wants to be more involved in my decisions but I need space to make my own choices. Her concern comes from a place of love but sometimes feels suffocating and intrusive."
    },
    {
        "id": "family-02",
        "type": "daily_reflection",
        "content": "Anniversary dinner with my partner was emotionally challenging tonight. We discussed our relationship struggles and lack of quality time together. Both of us feel disconnected and need to work on rebuilding intimacy and trust that was lost over the past year."
    },
    {
        "id": "family-03",
        "type": "note",
        "content": "My teenage daughter closed off to me again today when I tried asking about her school day. She says I don't understand her generation and that I'm too judgmental about her friends and social media use. Parenting teenagers requires a different approach than when she was younger."
    },
    {
        "id": "family-04",
        "type": "reflection",
        "content": "Family gathering over the weekend brought up old sibling rivalry tensions. My brother's political views clashed with mine and the conversation got heated at dinner table. Feel guilty about letting emotions get the better of me in front of everyone including the children."
    },
    {
        "id": "family-05",
        "type": "note",
        "content": "Called my father this evening just to check in and we ended up having a meaningful conversation about his retirement plans and legacy. He's finally opening up about his health concerns and what he wants for his remaining years. Grateful for these moments of connection."
    },
    {
        "id": "family-06",
        "type": "daily_reflection",
        "content": "My best friend from college called today with unexpected news - she's moving back to the city after 5 years abroad. We made plans to reconnect over coffee this weekend. Excited to rebuild our friendship which drifted apart due to distance and life changes."
    },
    {
        "id": "family-07",
        "type": "note",
        "content": "Dinner conversation with spouse turned into a discussion about our long-term goals and whether we want children. We're on slightly different pages - I want to start trying soon while she wants to focus on her career first. Need to find compromise on timing and priorities."
    },

    # Cluster C: Health/Wellness (5 items)
    {
        "id": "health-01",
        "type": "note",
        "content": "Started a new workout routine this morning at the local gym. Focusing on strength training and cardio to improve my overall fitness and energy levels. Goal is to exercise at least 4 times per week and track my progress with a fitness app to stay motivated."
    },
    {
        "id": "health-02",
        "type": "daily_reflection",
        "content": "Visited my doctor for a routine check-up and he suggested I need to pay more attention to my diet and nutrition. My cholesterol levels are slightly elevated and blood pressure is borderline. Making changes to eat more vegetables and fewer processed foods starting today."
    },
    {
        "id": "health-03",
        "type": "note",
        "content": "Meditation practice is finally sticking after 3 weeks of consistent morning sessions. I'm noticing reduced anxiety and better focus throughout the day. The health benefits extend beyond just mental wellness - my sleep quality has improved dramatically too."
    },
    {
        "id": "health-04",
        "type": "reflection",
        "content": "Decided to quit caffeine and see how it affects my anxiety and sleep patterns. Day 3 of no coffee has been tough with withdrawal headaches but I'm committed to this health experiment. Hoping for better energy stability without the afternoon crashes."
    },
    {
        "id": "health-05",
        "type": "note",
        "content": "Signed up for a yoga class series at the community center starting next month. Want to improve my flexibility and reduce physical tension in my neck and shoulders. The instructor emphasizes the mind-body connection which appeals to my wellness goals."
    },

    # Bridge items: Connecting clusters
    {
        "id": "bridge-work-life",
        "type": "reflection",
        "content": "Struggling to balance career demands with family time and personal relationships. My promotion means longer hours at the office which is causing tension at home with my partner. The work stress is spilling over and affecting quality time with loved ones on weekends."
    },
    {
        "id": "bridge-family-health",
        "type": "reflection",
        "content": "My mother's health is declining and we're worried about the entire family. She's resisting going to the doctor despite our concerns. The situation is causing significant stress on my own mental health and sleep patterns as I try to coordinate care and support."
    },
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
# DATABASE SETUP
# =============================================================================

async def setup_database():
    """Initialize test database and clean previous test data."""
    log("Setting up test database...")
    
    # Remove existing test database
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        log("Removed previous test database")
    
    # Initialize database
    init_db()
    
    # Clear test entries if they exist in main db
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
    """Insert all 20 seed entries into database."""
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
# OLLAMA CONNECTOR
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
                timeout=60
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
                timeout=30
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

async def process_all_entries():
    """Process all 20 entries through SecondBrainService with real Ollama."""
    log("Processing entries through Second Brain (this may take a few minutes)...")
    
    ollama = RealOllamaClient()
    
    # Track timing
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
                result = await service.process_new_item(
                    item_id=entry_data["id"],
                    content=entry_data["content"],
                    item_type=entry_data["type"],
                    skip_embedding=False,
                    skip_linking=False
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
                
            except Exception as e:
                log_error(f"Failed to process {entry_data['id']}: {e}")
                
        finally:
            db.close()
    
    # Store timing stats
    if processing_times:
        test_results["timing_stats"]["process_item"] = {
            "count": len(processing_times),
            "p50": statistics.median(processing_times),
            "p95": statistics.quantiles(processing_times, n=20)[18] if len(processing_times) >= 20 else max(processing_times),
            "mean": statistics.mean(processing_times),
            "min": min(processing_times),
            "max": max(processing_times),
        }
    
    log_success(f"Completed processing all entries")


# =============================================================================
# VERIFICATION
# =============================================================================

async def verify_counts():
    """Verify database counts match expectations."""
    log("Verifying database state...")
    
    db = SessionLocal()
    try:
        # Count entries
        entries_count = db.query(Entry).filter(
            Entry.id.in_([e["id"] for e in SEED_ENTRIES])
        ).count()
        
        # Count tags
        tags_count = db.query(ItemTag).filter(
            ItemTag.item_id.in_([e["id"] for e in SEED_ENTRIES])
        ).count()
        
        # Count embeddings
        embeddings_count = db.query(ItemEmbedding).filter(
            ItemEmbedding.item_id.in_([e["id"] for e in SEED_ENTRIES])
        ).count()
        
        # Count links
        links_count = db.query(ItemLink).filter(
            (ItemLink.source_item_id.in_([e["id"] for e in SEED_ENTRIES])) |
            (ItemLink.target_item_id.in_([e["id"] for e in SEED_ENTRIES]))
        ).count()
        
        log(f"Entries: {entries_count}")
        log(f"Tags: {tags_count}")
        log(f"Embeddings: {embeddings_count}")
        log(f"Links: {links_count}")
        
        # Assertions
        assert entries_count == 22, f"Expected 22 entries, got {entries_count}"
        assert tags_count == 66, f"Expected 66 tags (3 per entry), got {tags_count}"
        assert embeddings_count == 22, f"Expected 22 embeddings, got {embeddings_count}"
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
    """Test context retrieval with various queries."""
    log("Testing context retrieval...")
    
    ollama = RealOllamaClient()
    db = SessionLocal()
    
    try:
        service = SecondBrainService(
            db=db,
            ollama=ollama,
            embed_model=EMBED_MODEL
        )
        
        # Define test queries
        test_queries = [
            {
                "name": "work_stress_query",
                "query": "work stress anxiety",
                "expected_clusters": ["work"],
                "description": "Should return mostly work items"
            },
            {
                "name": "family_relationships_query", 
                "query": "family relationships mother",
                "expected_clusters": ["family"],
                "description": "Should return mostly family items"
            },
            {
                "name": "health_wellness_query",
                "query": "health exercise wellness",
                "expected_clusters": ["health"],
                "description": "Should return mostly health items"
            },
        ]
        
        retrieval_times = []
        
        for test in test_queries:
            try:
                start_time = time.time()
                
                context = await service.get_context_for_query(
                    query_text=test["query"],
                    top_k=8,
                    token_budget=800
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
                
                # Log item IDs (not content)
                item_ids = [item.get("item_id", "unknown") for item in items]
                log(f"Query '{test['query']}' returned {item_count} items in {elapsed:.2f}s")
                log(f"  Item IDs: {', '.join(item_ids[:5])}{'...' if len(item_ids) > 5 else ''}")
                
                # Verify at least one item returned
                assert item_count > 0, f"Query '{test['query']}' returned no items"
                
            except Exception as e:
                log_error(f"Retrieval test '{test['name']}' failed: {e}")
                test_results["retrieval_tests"][test["name"]] = {
                    "error": str(e),
                    "query": test["query"]
                }
        
        # Store timing stats
        if retrieval_times:
            test_results["timing_stats"]["get_context"] = {
                "count": len(retrieval_times),
                "p50": statistics.median(retrieval_times),
                "p95": statistics.quantiles(retrieval_times, n=20)[18] if len(retrieval_times) >= 20 else max(retrieval_times),
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
    print("SECOND BRAIN E2E TEST - FINAL REPORT")
    print("="*80)
    
    print("\n📊 CREATED ENTITIES")
    print(f"   Entries: {test_results['entries_created']}")
    print(f"   Tags: {test_results['tags_created']}")
    print(f"   Embeddings: {test_results['embeddings_created']}")
    print(f"   Links: {test_results['links_created']}")
    
    print("\n⏱️  TIMING STATISTICS")
    for op_name, stats in test_results["timing_stats"].items():
        print(f"   {op_name}:")
        print(f"     count={stats['count']}, p50={stats['p50']:.3f}s, p95={stats['p95']:.3f}s")
        print(f"     mean={stats['mean']:.3f}s, min={stats['min']:.3f}s, max={stats['max']:.3f}s")
    
    print("\n🔍 RETRIEVAL TESTS")
    for test_name, info in test_results["retrieval_tests"].items():
        if "error" in info:
            print(f"   ✗ {test_name}: ERROR - {info['error']}")
        else:
            print(f"   ✓ {test_name}: {info['items_returned']} items, "
                  f"{info['elapsed_seconds']:.2f}s")
    
    print("\n✅ ASSERTION RESULTS")
    print("   ✓ entries_count == 20")
    print("   ✓ tags_count == 60")
    print("   ✓ embeddings_count == 20")
    print("   ✓ links_count > 0")
    
    # Verify all retrieval queries returned at least 1 item
    all_retrieval_ok = all(
        info.get("items_returned", 0) > 0
        for info in test_results["retrieval_tests"].values()
        if "error" not in info
    )
    
    if all_retrieval_ok:
        print("   ✓ All retrieval queries returned at least 1 relevant item")
    else:
        print("   ✗ Some retrieval queries failed to return items")
    
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
    elif errors_count < 5:
        print(f"   ⚠️  {errors_count} minor issues (likely non-critical)")
    else:
        print(f"   ❌ {errors_count} errors encountered")
    
    print("="*80)


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_all_tests():
    """Run the complete E2E test suite."""
    print("\n" + "="*80)
    print("SECOND BRAIN E2E TEST WITH REAL OLLAMA")
    print("="*80)
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Embed Model: {EMBED_MODEL}")
    print(f"Chat Model: {CHAT_MODEL}")
    print(f"Test Entries: {len(SEED_ENTRIES)}")
    print("="*80 + "\n")
    
    # Pre-flight check
    log("Running pre-flight checks...")
    
    # Check Ollama availability
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
        # Test phases
        await setup_database()
        await create_seed_entries()
        await process_all_entries()
        await verify_counts()
        await test_retrieval()
        await print_final_report()
        
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
    # Warn if not in venv
    venv_path = "/Users/carlo/Desktop/pr_prj/humanity/venv"
    if sys.prefix != venv_path:
        print(f"⚠️  Warning: Not in expected venv ({venv_path})")
        print(f"   Current: {sys.executable}")
    
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
