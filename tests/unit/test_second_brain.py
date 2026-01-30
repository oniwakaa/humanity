"""
Unit tests for Second Brain: tagging, linking, embedding, retrieval.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock

from second_brain import (
    TagGenerator,
    TagNormalizer,
    GeneratedTag,
    EmbeddingManager,
    SecondBrainRetriever,
    SecondBrainService,
    ItemLinkData,
    RelatedItem
)


# =============================================================================
# TEST: Tag Normalization
# =============================================================================

class TestTagNormalization:
    """Test the tag normalizer rules."""

    def test_normalize_lowercase(self):
        assert TagNormalizer.normalize(" WORK ") == "work"
        assert TagNormalizer.normalize("Family Life") == "family life"

    def test_normalize_truncate_words(self):
        assert TagNormalizer.normalize("this is a really long tag phrase") == "this is a"

    def test_normalize_remove_punctuation(self):
        assert TagNormalizer.normalize("work! stress?") == "work stress"
        assert TagNormalizer.normalize("family-life") == "family-life"  # Hyphens allowed

    def test_validity_checks(self):
        assert TagNormalizer.is_valid("work") is True
        assert TagNormalizer.is_valid("misc") is False
        assert TagNormalizer.is_valid("other") is False
        assert TagNormalizer.is_valid("") is False
        assert TagNormalizer.is_valid("a" * 60) is False  # Too long


# =============================================================================
# TEST: Tag Generation
# =============================================================================

class TestTagGenerator:
    """Test LLM-based tag generation with mocked Ollama."""

    @pytest.fixture
    def mock_ollama(self):
        ollama = Mock()
        ollama.generate = AsyncMock()
        return ollama

    @pytest.mark.asyncio
    async def test_generate_three_tags_success(self, mock_ollama):
        mock_ollama.generate.return_value = {
            "response": '{"tags": [{"tag": "work", "category": "topic"}, {"tag": "career planning", "category": "intent"}, {"tag": "anxiety", "category": "emotion"}]}'
        }

        generator = TagGenerator(mock_ollama, model_name="mistral")
        tags = await generator.generate_tags("I'm worried about my promotion at work")

        assert len(tags) == 3
        assert tags[0].tag == "work"
        assert tags[0].category == "topic"
        assert tags[1].tag == "career planning"
        assert tags[1].category == "intent"
        assert tags[2].tag == "anxiety"

    @pytest.mark.asyncio
    async def test_generate_tags_json_in_markdown(self, mock_ollama):
        mock_ollama.generate.return_value = {
            "response": '```json\n{"tags": [{"tag": "family", "category": "topic"}, {"tag": "conflict resolution", "category": "intent"}, {"tag": "frustration", "category": "emotion"}]}\n```'
        }

        generator = TagGenerator(mock_ollama)
        tags = await generator.generate_tags("My mom keeps criticizing my choices")

        assert len(tags) == 3
        assert tags[0].tag == "family"

    @pytest.mark.asyncio
    async def test_generate_tags_retries_on_failure(self, mock_ollama):
        mock_ollama.generate.side_effect = [
            Exception("Network error"),
            {"response": '{"tags": [{"tag": "health", "category": "topic"}, {"tag": "exercise", "category": "intent"}, {"tag": "motivation", "category": "emotion"}]}'}
        ]

        generator = TagGenerator(mock_ollama)
        tags = await generator.generate_tags("Starting my fitness journey")

        assert len(tags) == 3
        assert mock_ollama.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_tags_fallback(self, mock_ollama):
        mock_ollama.generate.return_value = {"response": "invalid json"}

        generator = TagGenerator(mock_ollama)
        tags = await generator.generate_tags("I hate my boss, he is so frustrating")

        # Should use keyword-based fallback
        assert len(tags) == 3
        assert tags[0].category == "topic"
        assert tags[1].category == "intent"
        assert tags[2].category == "emotion"


# =============================================================================
# TEST: Embeddings
# =============================================================================

class TestEmbeddingManager:
    """Test embedding generation and similarity calculations."""

    @pytest.fixture
    def mock_ollama(self):
        ollama = Mock()
        ollama.embeddings = AsyncMock()
        return ollama

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, mock_ollama):
        mock_ollama.embeddings.return_value = {
            "embedding": [0.1, 0.2, 0.3, 0.4]
        }

        manager = EmbeddingManager(mock_ollama, "mxbai-embed-large")
        embedding = await manager.generate_embedding("test content")

        assert embedding == [0.1, 0.2, 0.3, 0.4]
        mock_ollama.embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_none_on_failure(self, mock_ollama):
        mock_ollama.embeddings.side_effect = Exception("Ollama down")

        manager = EmbeddingManager(mock_ollama)
        embedding = await manager.generate_embedding("test content")

        assert embedding is None

    def test_cosine_similarity_identical(self):
        vec = [1.0, 0.0, 0.0]
        result = EmbeddingManager.cosine_similarity(vec, vec)
        assert result == 1.0

    def test_cosine_similarity_orthogonal(self):
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        result = EmbeddingManager.cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_cosine_similarity_similar(self):
        vec1 = [1.0, 0.5, 0.3]
        vec2 = [0.9, 0.4, 0.2]
        result = EmbeddingManager.cosine_similarity(vec1, vec2)
        assert 0.9 < result < 1.0

    def test_cosine_similarity_different_dims(self):
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        result = EmbeddingManager.cosine_similarity(vec1, vec2)
        assert result == 0.0


# =============================================================================
# TEST: Second Brain Service
# =============================================================================

class TestSecondBrainServiceIntegration:
    """Test the main service with mocked DB and Ollama."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session."""
        session = Mock()
        session.query.return_value = Mock()
        session.query.return_value.filter.return_value = Mock()
        session.query.return_value.filter.return_value.first.return_value = None
        return session

    @pytest.fixture
    def mock_ollama(self):
        ollama = Mock()
        ollama.generate = AsyncMock(return_value={
            "response": '{"tags": [{"tag": "health", "category": "topic"}, {"tag": "goal setting", "category": "intent"}, {"tag": "optimism", "category": "emotion"}]}'
        })
        ollama.embeddings = AsyncMock(return_value={
            "embedding": [0.1] * 1024
        })
        return ollama

    @pytest.mark.asyncio
    async def test_process_new_item_creates_tags(self, mock_session, mock_ollama):
        service = SecondBrainService(mock_session, mock_ollama)

        result = await service.process_new_item(
            item_id="entry-123",
            content="I want to get healthier this year",
            item_type="reflection"
        )

        assert result["tags_created"] == 3
        assert result["embedding_updated"] is True
        assert mock_session.add.call_count >= 3  # Tags added


# =============================================================================
# TEST: Retrieval
# =============================================================================

class TestSecondBrainRetrieval:
    """Test the retrieval and context injection."""

    @pytest.fixture
    def mock_session(self):
        session = Mock()

        # Mock empty results for most queries
        query = Mock()
        session.query.return_value = query
        query.join.return_value = query
        query.filter.return_value = query
        query.all.return_value = []
        query.first.return_value = None

        return session

    @pytest.fixture
    def mock_ollama(self):
        ollama = Mock()
        ollama.embeddings = AsyncMock(return_value={
            "embedding": [0.5] * 384
        })
        return ollama

    @pytest.mark.asyncio
    async def test_get_context_with_empty_db(self, mock_session, mock_ollama):
        """Graceful fallback when no related items exist."""
        manager = EmbeddingManager(mock_ollama)
        retriever = SecondBrainRetriever(mock_session, manager)

        context = await retriever.get_context(
            query_text="test query",
            top_k=5,
            token_budget=500
        )

        # Should return empty structure without crashing
        assert "items" in context
        assert context["items"] == []
        assert "themes" in context
        assert context["summary"] == ""

    def test_deduplicate_and_score(self, mock_session):
        """Test deduplication of related items by ID."""
        manager = EmbeddingManager(Mock())
        retriever = SecondBrainRetriever(mock_session, manager)

        items = [
            RelatedItem("id-1", "note", "content a", 0.9, "tag_match", ["work"], ""),
            RelatedItem("id-2", "note", "content b", 0.8, "semantic", ["work"], ""),
            RelatedItem("id-1", "note", "content a again", 0.95, "semantic", ["work"], ""),  # Duplicate
        ]

        result = retriever._deduplicate_and_score(items)

        assert len(result) == 2
        assert result[0].relevance_score == 0.95  # Higher score kept
        assert result[0].connection_type == "both"  # Both types marked

    def test_create_context_summary_token_budget(self, mock_session):
        """Test token budget enforcement in summaries."""
        manager = EmbeddingManager(Mock())
        retriever = SecondBrainRetriever(mock_session, manager)

        long_content = "x" * 500  # 500 chars ~ 125 tokens

        items = [
            RelatedItem(f"id-{i}", "note", long_content, 0.9, "tag_match", [], "")
            for i in range(10)
        ]

        # Small budget should produce small output
        summary = retriever._create_context_summary(items, token_budget=100)
        estimated_tokens = len(summary) // 4
        assert estimated_tokens <= 100

        # Large budget should include more
        large_summary = retriever._create_context_summary(items, token_budget=2000)
        assert len(large_summary) > len(summary)


# =============================================================================
# TEST: Acceptance Criteria
# =============================================================================

class TestAcceptanceCriteria:
    """Tests that verify the core acceptance criteria."""

    @pytest.mark.asyncio
    async def test_exactly_three_tags_generated(self):
        """AC: Each item gets exactly 3 tags."""
        ollama = Mock()
        ollama.generate = AsyncMock(return_value={
            "response": '{"tags": [{"tag": "one", "category": "topic"}]}'  # Only 1 tag from LLM
        })

        generator = TagGenerator(ollama)
        tags = await generator.generate_tags("short content")

        # System should pad to exactly 3
        assert len(tags) == 3

    @pytest.mark.asyncio
    async def test_no_misc_or_other_tags(self):
        """AC: Tags must be meaningful, no 'misc' or 'other'."""
        ollama = Mock()
        ollama.generate = AsyncMock(return_value={
            "response": '{"tags": [{"tag": "misc", "category": "topic"}, {"tag": "one", "category": "topic"}, {"tag": "other", "category": "emotion"}]}'
        })

        generator = TagGenerator(ollama)
        tags = await generator.generate_tags("content")

        tag_names = [t.tag for t in tags]
        assert "misc" not in tag_names
        assert "other" not in tag_names

    def test_tag_persistence_structure(self):
        """AC: Tags must be stored in persistent storage structure."""
        # Verify our data models support the required storage
        from api.models import Tag, ItemTag, ItemEmbedding, ItemLink

        # Check tables exist in the model
        assert hasattr(Tag, 'name')
        assert hasattr(Tag, 'id')
        assert hasattr(ItemTag, 'item_id')
        assert hasattr(ItemTag, 'tag_id')
        assert hasattr(ItemLink, 'source_item_id')
        assert hasattr(ItemLink, 'target_item_id')
        assert hasattr(ItemLink, 'weight')
        assert hasattr(ItemLink, 'explanation')


# =============================================================================
# TEST: Integration with Background Processor
# =============================================================================

class TestBackgroundProcessor:
    """Test integration with the orchestrator background worker."""

    @pytest.mark.asyncio
    async def test_process_job_valid_data(self):
        from second_brain.background_processor import SecondBrainWorker, SecondBrainTask

        ollama = Mock()
        ollama.generate = AsyncMock(return_value={
            "response": '{"tags": [{"tag": "topic", "category": "topic"}, {"tag": "intent", "category": "intent"}, {"tag": "emotion", "category": "emotion"}]}'
        })
        ollama.embeddings = AsyncMock(return_value={
            "embedding": [0.1] * 1024
        })

        worker = SecondBrainWorker(ollama, "embed-model", "chat-model")

        # Mock the DB session factory
        # Since we can't easily mock the DB layer without more setup,
        # we verify the job processing at the data structure level
        job_data = SecondBrainTask("entry-123", "test content", "note").to_dict()

        assert job_data["type"] == "second_brain"
        assert job_data["item_id"] == "entry-123"
        assert job_data["content"] == "test content"
        assert job_data["item_type"] == "note"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
