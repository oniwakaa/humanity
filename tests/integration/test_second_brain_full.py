"""
Integration Test: Second Brain Full Pipeline
=============================================

This test verifies:
1. Entry creation and processing through SecondBrainService
2. Tag verification (exactly 3 tags per entry)
3. Link creation (tag-based and semantic)
4. Context retrieval for AI personalization queries
5. Context injection formatting

Uses real SQLite database with mocked Ollama responses.
"""

import asyncio
import asyncio
import json
import os
import sys
import sqlite3
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

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
)


# =============================================================================
# MOCK OLLAMA ADAPTER
# =============================================================================

class MockOllamaAdapter:
    """Mock Ollama that returns predictable responses for testing."""
    
    def __init__(self, tag_responses: dict = None, embeddings: List[List[float]] = None):
        self.tag_responses = tag_responses or {}
        self.embeddings_cache = embeddings or {}
        self.embed_idx = 0
        # Store which tags have been assigned to entries
        self.tag_cache = {}
    
    async def generate(self, prompt: str, model=None, system=None, temperature=0.3, max_tokens=150, 
                       tools=None, tool_choice=None, schema=None):
        """Return predefined tag response based on content keywords."""
        # Extract content from the prompt (comes last)
        content_start = prompt.lower().find('content to analyze:')
        if content_start > 0:
            content = prompt[content_start + 19:].lower()
        else:
            content = prompt.lower()
        
        # Check for specific content patterns and return distinct tags
        entry_id = None
        for entry in TEST_ENTRIES:
            if entry["content"].lower() in content[:100]:
                entry_id = entry["id"]
                break
        
        if entry_id and entry_id in self.tag_cache:
            return {"response": self.tag_cache[entry_id]}
        
        # Default tags based on content - check the full content, not just the prompt
        if 'stress' in content or 'work' in content and 'boss' in content:
            tags = '{"tags": [{"tag": "work", "category": "topic"}, {"tag": "stress management", "category": "intent"}, {"tag": "anxiety", "category": "emotion"}]}'
        elif 'family' in content or 'mother' in content.lower() or 'joy' in content:
            tags = '{"tags": [{"tag": "family", "category": "topic"}, {"tag": "celebration", "category": "intent"}, {"tag": "happiness", "category": "emotion"}]}'
        elif 'health' in content or 'exercise' in content or 'wellness' in content:
            tags = '{"tags": [{"tag": "health", "category": "topic"}, {"tag": "goal setting", "category": "intent"}, {"tag": "growth", "category": "emotion"}]}'
        elif 'travel' in content or 'japan' in content or 'trip' in content:
            tags = '{"tags": [{"tag": "travel", "category": "topic"}, {"tag": "planning", "category": "intent"}, {"tag": "excitement", "category": "emotion"}]}'
        elif 'art' in content or 'creative' in content or 'watercolor' in content:
            tags = '{"tags": [{"tag": "creativity", "category": "topic"}, {"tag": "art exploration", "category": "intent"}, {"tag": "inspiration", "category": "emotion"}]}'
        else:
            tags = '{"tags": [{"tag": "personal reflection", "category": "topic"}, {"tag": "processing", "category": "intent"}, {"tag": "contemplation", "category": "emotion"}]}'
        
        if entry_id:
            self.tag_cache[entry_id] = tags
        
        response = {"response": tags}
        return response
    
    async def embeddings(self, model: str, prompt: str):
        """Generate predictable embeddings based on content hash."""
        # Check cache first
        cache_key = (model, prompt[:100])
        if cache_key in getattr(self, '_embed_cache', {}):
            return {"embedding": self._embed_cache[cache_key]}
        
        if not hasattr(self, '_embed_cache'):
            self._embed_cache = {}
        
        # Generate unique but consistent embedding based on content
        import hashlib
        
        # Create a deterministic vector from the content
        content_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
        vec_length = 384
        
        # Work-related gets one cluster
        if 'work' in prompt.lower() or 'stress' in prompt.lower() or 'job' in prompt.lower() or 'boss' in prompt.lower():
            base_seed = 1000
        # Family-related gets another
        elif 'family' in prompt.lower() or 'joy' in prompt.lower() or 'mother' in prompt.lower() or 'parent' in prompt.lower():
            base_seed = 2000
        # Health-related gets another
        elif 'health' in prompt.lower() or 'exercise' in prompt.lower() or 'wellness' in prompt.lower():
            base_seed = 3000
        # Travel-related
        elif 'travel' in prompt.lower() or 'japan' in prompt.lower() or 'trip' in prompt.lower():
            base_seed = 4000
        # Creative-related
        elif 'creative' in prompt.lower() or 'art' in prompt.lower() or 'project' in prompt.lower():
            base_seed = 5000
        else:
            base_seed = 9000
        
        # Generate deterministic vector
        import random
        random.seed(base_seed + content_hash % 1000)
        embedding = [random.uniform(-1, 1) for _ in range(vec_length)]
        
        # Normalize for cosine similarity
        import math
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x/norm for x in embedding]
        
        self._embed_cache[cache_key] = embedding
        return {"embedding": embedding}
    
    async def embed(self, model: str, prompt: str):
        """Alias for embeddings method - some adapters use embed()."""
        return await self.embeddings(model, prompt)


# =============================================================================
# TEST DATA
# =============================================================================

TEST_ENTRIES = [
    {
        "id": "entry-work-01",
        "content": "Had a really stressful day at work today. Meeting ran over, boss critiqued my presentation, and I feel overwhelmed. Need to figure out how to manage work stress better.",
        "expected_tags": ["work", "stress management", "anxiety"],
        "feature_type": "free_diary"
    },
    {
        "id": "entry-family-01",
        "content": "Beautiful day with the family. My mother cooked her special recipe and we laughed together. Feeling so grateful for these joyful moments. Family time truly brings me happiness.",
        "expected_tags": ["family", "celebration", "happiness"],
        "feature_type": "free_diary"
    },
    {
        "id": "entry-health-01",
        "content": "Starting my health journey today. I want to exercise more, eat healthier, and sleep better. Setting clear goals to improve my wellness and build better habits for the future.",
        "expected_tags": ["health", "goal setting", "growth"],
        "feature_type": "reflection"
    },
    {
        "id": "entry-travel-01",
        "content": "Planning a trip to Japan next month. So excited to explore Tokyo, visit temples, and try authentic ramen. Need to book hotels and create an itinerary for this adventure.",
        "expected_tags": ["travel", "planning", "excitement"],
        "feature_type": "your_story"
    },
    {
        "id": "entry-creative-01",
        "content": "Started a new art project today. Experimenting with watercolor and mixed media. Finding inspiration in nature. Creative expression helps me process my emotions and brings peace.",
        "expected_tags": ["creativity", "art exploration", "inspiration"],
        "feature_type": "daily_questions_answ"
    },
]


# =============================================================================
# RESULT TRACKING
# =============================================================================

test_results = {
    "errors": [],
    "entries_created": 0,
    "tags_per_entry": {},
    "total_tags_created": 0,
    "total_links_created": 0,
    "retrieval_tests": {},
    "links_by_entry": {},
}


def log_success(message: str):
    """Log successful test step."""
    print(f"✓ {message}")


def log_error(message: str):
    """Log error and track it."""
    test_results["errors"].append(message)
    print(f"✗ ERROR: {message}")


def log_info(message: str):
    """Log informational message."""
    print(f"  → {message}")


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

async def setup_database():
    """Initialize database and clear test data."""
    log_info("Initializing database...")
    
    # Ensure database exists
    init_db()
    
    # Clear any existing test entries
    db = SessionLocal()
    try:
        for entry in TEST_ENTRIES:
            # Delete in proper order (links, tags, embeddings, entries)
            db.execute(text(f"DELETE FROM item_links WHERE source_item_id = '{entry['id']}' OR target_item_id = '{entry['id']}'"))
            db.execute(text(f"DELETE FROM item_tags WHERE item_id = '{entry['id']}'"))
            db.execute(text(f"DELETE FROM item_embeddings WHERE item_id = '{entry['id']}'"))
            db.execute(text(f"DELETE FROM entries WHERE id = '{entry['id']}'"))
        db.commit()
        log_success("Database initialized and cleaned")
    except Exception as e:
        log_error(f"Database cleanup failed: {e}")
    finally:
        db.close()


async def create_test_entries():
    """Create test entries in the database."""
    log_info("Creating test entries...")
    
    db = SessionLocal()
    try:
        for entry_data in TEST_ENTRIES:
            entry = Entry(
                id=entry_data["id"],
                text=entry_data["content"],
                feature_type=entry_data["feature_type"]
            )
            db.add(entry)
        
        db.commit()
        test_results["entries_created"] = len(TEST_ENTRIES)
        log_success(f"Created {len(TEST_ENTRIES)} test entries")
    except Exception as e:
        log_error(f"Failed to create entries: {e}")
    finally:
        db.close()


async def process_entries_with_second_brain():
    """Process all entries through SecondBrainService."""
    log_info("Processing entries through Second Brain...")
    
    mock_ollama = MockOllamaAdapter()
    db = SessionLocal()
    
    try:
        service = SecondBrainService(
            db=db,
            ollama=mock_ollama,
            embed_model="mxbai-embed-large:latest",
            chat_model="mistral:latest"
        )
        
        for entry_data in TEST_ENTRIES:
            try:
                result = await service.process_new_item(
                    item_id=entry_data["id"],
                    content=entry_data["content"],
                    item_type=entry_data["feature_type"],
                    skip_embedding=False,
                    skip_linking=False
                )
                
                # Track results
                test_results["tags_per_entry"][entry_data["id"]] = {
                    "created": result["tags_created"],
                    "expected": 3,
                    "errors": result["errors"]
                }
                
                if result["errors"]:
                    test_results["errors"].extend(result["errors"])
                
                log_success(f"Processed entry {entry_data['id']}: {result['tags_created']} tags, embedding={result['embedding_updated']}, {result['links_created']} links")
                
            except Exception as e:
                log_error(f"Failed to process {entry_data['id']}: {e}")
    finally:
        db.close()


async def verify_tags():
    """Verify each entry has exactly 3 tags stored."""
    log_info("Verifying tags in database...")
    
    db = SessionLocal()
    try:
        total_tags = 0
        
        for entry_data in TEST_ENTRIES:
            # Count tags for this entry
            tags = db.query(Tag).join(ItemTag).filter(ItemTag.item_id == entry_data["id"]).all()
            tag_names = [t.name for t in tags]
            tag_count = len(tags)
            total_tags += tag_count
            
            # Verify exactly 3 tags
            if tag_count == 3:
                log_success(f"Entry {entry_data['id']} has exactly 3 tags: {tag_names}")
            else:
                log_error(f"Entry {entry_data['id']} has {tag_count} tags (expected 3): {tag_names}")
        
        test_results["total_tags_created"] = total_tags
        log_info(f"Total tags created: {total_tags}")
    finally:
        db.close()


async def verify_links():
    """Verify links were created between related entries."""
    log_info("Verifying knowledge graph links...")
    
    db = SessionLocal()
    try:
        total_links = 0
        
        for entry_data in TEST_ENTRIES:
            # Get all links involving this entry
            outgoing = db.query(ItemLink).filter(ItemLink.source_item_id == entry_data["id"]).all()
            incoming = db.query(ItemLink).filter(ItemLink.target_item_id == entry_data["id"]).all()
            
            all_links = outgoing + incoming
            link_count = len(all_links)
            total_links += link_count
            
            test_results["links_by_entry"][entry_data["id"]] = {
                "count": link_count,
                "links": []
            }
            
            for link in all_links:
                other_id = link.target_item_id if link.source_item_id == entry_data["id"] else link.source_item_id
                test_results["links_by_entry"][entry_data["id"]]["links"].append({
                    "type": link.link_type,
                    "other_id": other_id,
                    "weight": link.weight
                })
            
            log_info(f"Entry {entry_data['id']} has {link_count} links")
            for link_info in test_results["links_by_entry"][entry_data["id"]]["links"]:
                log_info(f"  - {link_info['type']} link to {link_info['other_id'][:20]}... (weight: {link_info['weight']})")
        
        test_results["total_links_created"] = total_links
        log_success(f"Total links created: {total_links}")
    finally:
        db.close()


async def test_retrieval():
    """Test getSecondBrainContext with sample queries."""
    log_info("Testing context retrieval...")
    
    mock_ollama = MockOllamaAdapter()
    db = SessionLocal()
    
    try:
        service = SecondBrainService(
            db=db,
            ollama=mock_ollama,
            embed_model="mxbai-embed-large:latest"
        )
        
        # Test queries
        queries = [
            {
                "query": "I'm stressed about work",
                "expected_relevant": ["entry-work-01"],
                "description": "Work stress query"
            },
            {
                "query": "Feeling happy with family",
                "expected_relevant": ["entry-family-01"],
                "description": "Family joy query"
            },
            {
                "query": "Health and wellness goals",
                "expected_relevant": ["entry-health-01"],
                "description": "Health goals query"
            },
        ]
        
        for test in queries:
            try:
                context = await service.get_context_for_query(
                    query_text=test["query"],
                    top_k=5,
                    token_budget=800
                )
                
                # Check if expected entries were returned
                returned_items = context["items"]
                returned_ids = [item.get("item_id", item.get("id", "unknown")) for item in returned_items]
                
                test_results["retrieval_tests"][test["description"]] = {
                    "query": test["query"],
                    "items_returned": len(returned_items),
                    "returned_ids": returned_ids,
                    "expected_ids": test["expected_relevant"],
                    "matched": bool(set(test["expected_relevant"]) & set(returned_ids)) if returned_ids else False
                }
                
                if returned_items:
                    log_success(f"Query '{test['query'][:30]}...' returned {len(returned_items)} items")
                    for item in returned_items:
                        item_id = item.get("item_id", item.get("id", "???"))
                        score = item.get("relevance_score", "?")
                        conn_type = item.get("connection_type", "?")
                        log_info(f"  - {item_id[:20]}... (score: {score}, type: {conn_type})")
                else:
                    log_error(f"Query '{test['query'][:30]}...' returned NO items")
                
                # Test context formatting for prompt injection
                summary = context.get("summary", "")
                if summary:
                    log_success(f"Context summary generated ({len(summary)} chars, ~{len(summary)//4} tokens)")
                    log_info(f"Summary preview: {summary[:150]}...")
                else:
                    log_info(f"No context summary generated (empty result)")
                    
            except Exception as e:
                log_error(f"Retrieval test failed for '{test['query']}': {e}")
                import traceback
                traceback.print_exc()
    finally:
        db.close()


async def print_final_report():
    """Print comprehensive test report."""
    print("\n" + "="*80)
    print("SECOND BRAIN INTEGRATION TEST - FINAL REPORT")
    print("="*80)
    
    print(f"\n📊 ENTRIES CREATED")
    print(f"   Total: {test_results['entries_created']} test entries")
    
    print(f"\n🏷️  TAGS ASSIGNED")
    print(f"   Total tags created: {test_results['total_tags_created']}")
    for entry_id, info in test_results["tags_per_entry"].items():
        status = "✓" if info["created"] == 3 else "✗"
        print(f"   {status} {entry_id}: {info['created']} tags (expected {info['expected']})")
    
    print(f"\n🔗 LINKS CREATED")
    print(f"   Total links: {test_results['total_links_created']}")
    for entry_id, info in test_results["links_by_entry"].items():
        if info["links"]:
            print(f"   • {entry_id}: {info['count']} links")
            for link in info["links"][:3]:  # Show first 3 links
                print(f"     - {link['type']} to {link['other_id'][:25]}... (weight: {link['weight']})")
            if len(info["links"]) > 3:
                print(f"     ... and {len(info['links']) - 3} more")
    
    print(f"\n🔍 RETRIEVAL TESTS")
    for test_name, info in test_results["retrieval_tests"].items():
        status = "✓" if info["matched"] else "?"
        print(f"   {status} {test_name}")
        print(f"     Query: '{info['query']}'")
        print(f"     Items returned: {info['items_returned']}")
        if info['expected_ids']:
            found = set(info['expected_ids']) & set(info['returned_ids']) if info['returned_ids'] else set()
            if found:
                print(f"     ✓ Found expected entry: {list(found)[0]}")
            else:
                print(f"     ⚠ Expected {info['expected_ids'][0]} but not in top results")
        if info['returned_ids']:
            print(f"     Returned: {', '.join(info['returned_ids'][:3])}")
    
    print(f"\n⚠️  ERRORS ENCOUNTERED")
    if test_results["errors"]:
        print(f"   Total errors: {len(test_results['errors'])}")
        for error in test_results["errors"][:10]:
            print(f"   • {error}")
        if len(test_results["errors"]) > 10:
            print(f"   ... and {len(test_results['errors']) - 10} more")
    else:
        print("   NONE - All tests passed!")
    
    print(f"\n📈 SUMMARY")
    success_rate = 0
    if test_results["entries_created"] == len(TEST_ENTRIES):
        print("   ✓ All entries created successfully")
        success_rate += 25
    if test_results["total_tags_created"] == len(TEST_ENTRIES) * 3:
        print("   ✓ All tags assigned correctly (3 per entry)")
        success_rate += 25
    if test_results["total_links_created"] > 0:
        print(f"   ✓ Knowledge graph has {test_results['total_links_created']} links")
        success_rate += 25
    if test_results["retrieval_tests"] and any(t["items_returned"] > 0 for t in test_results["retrieval_tests"].values()):
        print("   ✓ Retrieval system returning results")
        success_rate += 25
    
    print(f"\n   Overall: {success_rate}% of core features operational")
    print("="*80)


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_all_tests():
    """Run the complete integration test suite."""
    print("\n" + "="*80)
    print("SECOND BRAIN INTEGRATION TEST")
    print("="*80)
    print(f"Database: SQLite at /Users/carlo/Desktop/pr_prj/humanity/humanity.db")
    print(f"Test entries: {len(TEST_ENTRIES)}")
    print(f"Ollama mock: Deterministic responses based on content keywords")
    print("="*80 + "\n")
    
    try:
        # Run all test phases
        await setup_database()
        await create_test_entries()
        await process_entries_with_second_brain()
        await verify_tags()
        await verify_links()
        await test_retrieval()
        await print_final_report()
        
    except Exception as e:
        print(f"\n✗ TEST RUN FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # Ensure we're in the right virtualenv
    venv_path = "/Users/carlo/Desktop/pr_prj/humanity/venv"
    if sys.prefix != venv_path:
        print(f"⚠️  Warning: Not running in expected venv at {venv_path}")
        print(f"   Current Python: {sys.executable}")
    
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
