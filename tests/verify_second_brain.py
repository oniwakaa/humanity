# Second Brain: Run Manual Verification
# This script verifies the Second Brain implementation without pytest

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from second_brain import (
    TagGenerator,
    TagNormalizer,
    GeneratedTag,
    EmbeddingManager,
    SecondBrainRetriever,
    ItemLinkData,
    RelatedItem
)

# Color output
def green(text): return f"\033[92m{text}\033[0m"
def red(text): return f"\033[91m{text}\033[0m"
def blue(text): return f"\033[94m{text}\033[0m"

def test_tag_normalization():
    """Test tag normalizer rules."""
    tests = [
        (" WORK ", "work"),
        ("Family Life", "family life"),
        ("this is a really long tag phrase", "this is a"),
        ("work! stress?", "work stress"),
        ("family-life", "family-life"),
    ]

    print(blue("\n[Test] Tag Normalization"))
    all_passed = True
    for input_val, expected in tests:
        result = TagNormalizer.normalize(input_val)
        passed = result == expected
        status = '✓' if passed else '✗'
        print(f"  {status} normalize('{input_val}') -> '{result}'")
        if not passed:
            print(f"    expected: '{expected}', got '{result}'")
            all_passed = False

    # Validity checks
    validity_tests = [
        ("work", True),
        ("misc", False),
        ("other", False),
        ("", False),
        ("a" * 60, False),
    ]

    for tag, expected in validity_tests:
        result = TagNormalizer.is_valid(tag)
        passed = result == expected
        status = '✓' if passed else '✗'
        print(f"  {status} is_valid('{tag[:20]}...') == {result}")
        if not passed:
            all_passed = False

    return all_passed


async def test_tag_generation():
    """Test tag generation with mocked Ollama."""
    print(blue("\n[Test] Tag Generation (3 tags)"))

    ollama = Mock()
    ollama.generate = AsyncMock(return_value={
        "response": '{"tags": [{"tag": "work", "category": "topic"}, {"tag": "career planning", "category": "intent"}, {"tag": "anxiety", "category": "emotion"}]}'
    })

    generator = TagGenerator(ollama, model_name="mistral")
    tags = await generator.generate_tags("I'm worried about my promotion at work")

    all_passed = True
    print(f"  Generated {len(tags)} tags")

    if len(tags) != 3:
        print(red(f"    ✗ Expected 3 tags, got {len(tags)}"))
        all_passed = False
    else:
        print(f"    ✓ Exactly 3 tags generated")

    expected_categories = ["topic", "intent", "emotion"]
    for i, tag in enumerate(tags):
        print(f"    Tag {i+1}: '{tag.tag}' (category: {tag.category})")
        if tag.category not in expected_categories:
            print(red(f"      ✗ Invalid category: {tag.category}"))
            all_passed = False

    return all_passed


async def test_embedding_manager():
    """Test embedding generation."""
    print(blue("\n[Test] Embedding Manager"))

    ollama = Mock()
    ollama.embeddings = AsyncMock(return_value={
        "embedding": [0.1, 0.2, 0.3, 0.4]
    })

    manager = EmbeddingManager(ollama, "mxbai-embed-large")
    embedding = await manager.generate_embedding("test content")

    all_passed = True
    if embedding == [0.1, 0.2, 0.3, 0.4]:
        print(f"  ✓ Embedding generated successfully")
    else:
        print(red(f"  ✗ Embedding mismatch"))
        all_passed = False

    # Test cosine similarity
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    sim = EmbeddingManager.cosine_similarity(vec1, vec2)

    if sim == 1.0:
        print(f"  ✓ Cosine similarity: identical vectors = 1.0")
    else:
        print(red(f"  ✗ Cosine similarity failed: {sim}"))
        all_passed = False

    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    sim = EmbeddingManager.cosine_similarity(vec1, vec2)

    if sim == 0.0:
        print(f"  ✓ Cosine similarity: orthogonal vectors = 0.0")
    else:
        print(red(f"  ✗ Orthogonal similarity failed: {sim}"))
        all_passed = False

    return all_passed


def test_data_model_integrity():
    """Test that data models have the correct structure."""
    print(blue("\n[Test] Data Model Structure"))

    try:
        from api.models import Tag, ItemTag, ItemEmbedding, ItemLink, Entry

        checks = [
            (hasattr(Tag, 'name'), "Tag has 'name'"),
            (hasattr(Tag, 'id'), "Tag has 'id'"),
            (hasattr(ItemTag, 'item_id'), "ItemTag has 'item_id'"),
            (hasattr(ItemTag, 'tag_id'), "ItemTag has 'tag_id'"),
            (hasattr(ItemLink, 'source_item_id'), "ItemLink has 'source_item_id'"),
            (hasattr(ItemLink, 'target_item_id'), "ItemLink has 'target_item_id'"),
            (hasattr(ItemLink, 'weight'), "ItemLink has 'weight'"),
            (hasattr(ItemLink, 'explanation'), "ItemLink has 'explanation'"),
            (hasattr(Entry, 'item_tags'), "Entry has 'item_tags' relationship"),
            (hasattr(Entry, 'embedding'), "Entry has 'embedding' relationship"),
            (hasattr(Entry, 'outgoing_links'), "Entry has 'outgoing_links' relationship"),
        ]

        all_passed = True
        for passed, desc in checks:
            status = '✓' if passed else '✗'
            print(f"  {status} {desc}")
            if not passed:
                all_passed = False

        return all_passed

    except ImportError as e:
        print(red(f"  ✗ Could not import data models: {e}"))
        return False


async def test_second_brain_service():
    """Test the main service."""
    print(blue("\n[Test] Second Brain Service"))

    from second_brain import SecondBrainService

    # Mock session
    session = Mock()
    session.query.return_value = Mock()
    session.query.return_value.filter.return_value = Mock()
    session.query.return_value.filter.return_value.first.return_value = None

    # Mock Ollama
    ollama = Mock()
    ollama.generate = AsyncMock(return_value={
        "response": '{"tags": [{"tag": "health", "category": "topic"}, {"tag": "goal setting", "category": "intent"}, {"tag": "optimism", "category": "emotion"}]}'
    })
    ollama.embeddings = AsyncMock(return_value={
        "embedding": [0.1] * 1024
    })

    service = SecondBrainService(session, ollama)

    result = await service.process_new_item(
        item_id="entry-123",
        content="I want to get healthier this year",
        item_type="reflection",
        skip_linking=True
    )

    all_passed = True
    print(f"  Result: {result}")

    if result.get("tags_created") == 3:
        print(f"  ✓ Created exactly 3 tags")
    else:
        print(red(f"  ✗ Expected 3 tags, got {result.get('tags_created')}"))
        all_passed = False

    if result.get("embedding_updated"):
        print(f"  ✓ Embedding stored")
    else:
        print(red(f"  ✗ Embedding not updated"))
        all_passed = False

    return all_passed


async def main():
    print(green("=" * 60))
    print(green("Second Brain Implementation Verification"))
    print(green("=" * 60))

    results = []

    # Run tests
    results.append(("Tag Normalization", test_tag_normalization()))
    results.append(("Tag Generation", await test_tag_generation()))
    results.append(("Embedding Manager", await test_embedding_manager()))
    results.append(("Data Model", test_data_model_integrity()))
    results.append(("Service Integration", await test_second_brain_service()))

    # Summary
    print(blue("\n" + "=" * 60))
    print(blue("Test Summary"))
    print(blue("=" * 60))

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = '✓' if result else '✗'
        print(f"  {status} {name}")

    print(green(f"\n{passed}/{total} test suites passed"))

    if passed == total:
        print(green("\n✓ All Second Brain components verified!"))
        return 0
    else:
        print(red("\n✗ Some tests failed"))
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
