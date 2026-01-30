# Second Brain: Tagging, Embeddings, Linking for Knowledge Graph
# Provides auto-tagging, semantic similarity matching, and knowledge retrieval

import json
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from second_brain.ollama_adapter import OllamaAsyncAdapter
from api.models import Entry, Tag, ItemTag, ItemEmbedding, ItemLink
from utils.telemetry import get_logger

logger = get_logger(__name__)

# Maintain alias for backward compatibility
OllamaConnector = OllamaAsyncAdapter

# Public API exports
__all__ = [
    "TagGenerator",
    "TagNormalizer",
    "GeneratedTag",
    "EmbeddingManager",
    "LinkBuilder",
    "SecondBrainRetriever",
    "SecondBrainService",
    "SecondBrainBackgroundProcessor",
    "ItemLinkData",
    "RelatedItem",
    "OllamaAsyncAdapter",
]

logger = get_logger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GeneratedTag:
    """Represents a generated tag with category hints."""
    tag: str
    category: str  # 'topic' | 'intent' | 'emotion'


@dataclass
class ItemLinkData:
    """Data structure for a knowledge graph link."""
    source_id: str
    target_id: str
    link_type: str  # 'tag_match' | 'semantic'
    weight: float
    explanation: str


@dataclass
class RelatedItem:
    """A related item returned from second brain retrieval."""
    item_id: str
    item_type: str
    content_preview: str  # First ~150 chars
    relevance_score: float
    connection_type: str  # 'shared_tag' | 'semantic_similarity' | 'both'
    shared_tags: List[str]
    explanation: str


# =============================================================================
# CONFIGURATION
# =============================================================================

TAG_GENERATION_PROMPT = """Analyze this user content and generate EXACTLY 3 tags.
Rules:
- Tags must be lowercase noun-phrases, 1-3 words, no punctuation, no emojis
- Tag 1 (topic): The main subject/topic area (e.g., "work", "family", "health")
- Tag 2 (intent/problem): What the user is trying to do or solve (e.g., "decision making", "stress relief", "planning")
- Tag 3 (emotion/value/theme): The emotional tone or core value (e.g., "anxiety", "gratitude", "growth")

If uncertain, provide reasonable interpretations. Never output "other" or "misc".

Respond ONLY with valid JSON in this exact format with double curly braces:
{{"tags": [{{"tag": "topic-tag", "category": "topic"}}, {{"tag": "intent-tag", "category": "intent"}}, {{"tag": "emotion-tag", "category": "emotion"}}]}}

Content to analyze: {content}"""

SUMMARY_GENERATION_PROMPT = """Create a 1-sentence summary of this content for context injection:
""" + "{content}" + """
Max 20 words. Focus on the key insight or concern."""

LINK_EXPLANATION_PROMPT = """Explain in 1 sentence why these two pieces of content are connected:

Content A: """ + "{source_preview}" + """

Content B: """ + "{target_preview}" + """

Connection reason: {link_reason}
Max 15 words."""


class TagNormalizer:
    """Normalizes and validates generated tags."""

    @staticmethod
    def normalize(tag: str) -> str:
        """
        Normalize a tag to standards:
        - Lowercase
        - Remove punctuation
        - Strip whitespace
        - Limit to 3 words
        """
        # Lowercase and remove punctuation except spaces and hyphens
        cleaned = re.sub(r'[^\w\s-]', '', tag.lower())
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        # Limit to first 3 words
        words = cleaned.split()[:3]
        return ' '.join(words)

    @staticmethod
    def is_valid(tag: str) -> bool:
        """Check if a tag meets basic validity criteria."""
        normalized = TagNormalizer.normalize(tag)
        if not normalized:
            return False
        if len(normalized) > 50:  # Reasonable max length
            return False
        # Check for forbidden words
        forbidden = {'misc', 'other', 'unknown', 'unspecified'}
        if normalized in forbidden:
            return False
        return True


class TagGenerator:
    """Generates exactly 3 tags for content using local LLM."""

    def __init__(self, ollama: OllamaConnector, model_name: Optional[str] = None):
        self.ollama = ollama
        self.model_name = model_name

    async def generate_tags(self, content: str, max_retries: int = 2) -> List[GeneratedTag]:
        """
        Generate exactly 3 tags for the content.
        Returns list of GeneratedTag dataclass.
        """
        # Truncate very long content for prompt efficiency
        truncated = content[:2000] if len(content) > 2000 else content

        prompt = TAG_GENERATION_PROMPT.format(content=truncated)

        for attempt in range(max_retries + 1):
            try:
                response = await self.ollama.generate(
                    prompt=prompt,
                    model=self.model_name,
                    system="You are a precise tagging system. Always output valid JSON with exactly 3 tags.",
                    temperature=0.3,
                    max_tokens=150
                )

                tags = self._parse_tag_response(response.get('response', ''))

                if len(tags) == 3:
                    return tags
                elif len(tags) > 0:
                    # Pad or truncate to exactly 3
                    while len(tags) < 3:
                        tags.append(GeneratedTag(tag=f"theme-{len(tags)+1}", category="emotion"))
                    return tags[:3]

            except Exception as e:
                logger.warning(f"Tag generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    break
                await asyncio.sleep(0.5)

        # Fallback: Generate basic tags
        return self._fallback_tags(content)

    def _parse_tag_response(self, response: str) -> List[GeneratedTag]:
        """Parse JSON response from LLM into GeneratedTag list."""
        try:
            # Extract JSON from markdown code blocks if present
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]

            data = json.loads(response.strip())
            tags = []

            for item in data.get('tags', []):
                tag_text = TagNormalizer.normalize(item.get('tag', ''))
                if TagNormalizer.is_valid(tag_text):
                    tags.append(GeneratedTag(
                        tag=tag_text,
                        category=item.get('category', 'topic')
                    ))

            return tags
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            logger.warning(f"Failed to parse tag response: {e}")
            return []

    def _fallback_tags(self, content: str) -> List[GeneratedTag]:
        """Generate basic fallback tags when LLM fails."""
        content_lower = content.lower()

        # Simple keyword-based fallbacks
        topic = "personal reflection"
        if any(w in content_lower for w in ['work', 'job', 'career', 'office', 'boss']):
            topic = "work"
        elif any(w in content_lower for w in ['family', 'parent', 'child', 'mother', 'father']):
            topic = "family"
        elif any(w in content_lower for w in ['health', 'exercise', 'sleep', 'doctor']):
            topic = "health"
        elif any(w in content_lower for w in ['goal', 'plan', 'future', 'dream']):
            topic = "goals"

        intent = "processing thoughts"
        if any(w in content_lower for w in ['help', 'advice', 'what should', 'how do']):
            intent = "seeking guidance"
        elif any(w in content_lower for w in ['angry', 'frustrated', 'upset', 'annoyed']):
            intent = "venting frustration"
        elif any(w in content_lower for w in ['happy', 'excited', 'celebrate', 'grateful']):
            intent = "celebrating joy"

        emotion = "contemplation"
        if any(w in content_lower for w in ['anxious', 'worried', 'stress', 'nervous']):
            emotion = "anxiety"
        elif any(w in content_lower for w in ['grateful', 'thankful', 'blessed']):
            emotion = "gratitude"
        elif any(w in content_lower for w in ['sad', 'depressed', 'lonely', 'grief']):
            emotion = "sadness"
        elif any(w in content_lower for w in ['hope', 'optimistic', 'better']):
            emotion = "hope"

        return [
            GeneratedTag(tag=topic, category="topic"),
            GeneratedTag(tag=intent, category="intent"),
            GeneratedTag(tag=emotion, category="emotion")
        ]


class EmbeddingManager:
    """Manages embeddings for semantic similarity."""

    def __init__(self, ollama: OllamaConnector, embed_model: str = "mxbai-embed-large:latest"):
        self.ollama = ollama
        self.embed_model = embed_model

    async def generate_embedding(self, content: str) -> Optional[List[float]]:
        """Generate embedding vector for content."""
        try:
            # Truncate for embedding model context window
            truncated = content[:3000] if len(content) > 3000 else content

            response = await self.ollama.embeddings(
                model=self.embed_model,
                prompt=truncated
            )

            embedding = response.get('embedding')
            if embedding and isinstance(embedding, list):
                return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")

        return None

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(a * a for a in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class LinkBuilder:
    """Builds knowledge graph links between items."""

    def __init__(self, db: Session, embedding_manager: EmbeddingManager, ollama: OllamaConnector):
        self.db = db
        self.embedding_manager = embedding_manager
        self.ollama = ollama

    async def build_links_for_item(self, item_id: str, max_semantic_links: int = 5) -> List[ItemLinkData]:
        """
        Build all links for a new item:
        1. Tag-match links (exact tag overlap)
        2. Semantic similarity links (top N closest embeddings)
        """
        links = []

        # Build tag-match links
        tag_links = await self._build_tag_links(item_id)
        links.extend(tag_links)

        # Build semantic links
        semantic_links = await self._build_semantic_links(item_id, max_semantic_links)
        links.extend(semantic_links)

        return links

    async def _build_tag_links(self, item_id: str) -> List[ItemLinkData]:
        """Find items sharing tags with the source item."""
        # Get item's tags
        item_tags = (
            self.db.query(Tag.name, Tag.id)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .filter(ItemTag.item_id == item_id)
            .all()
        )

        if not item_tags:
            return []

        tag_names = [t[0] for t in item_tags]
        tag_ids = [t[1] for t in item_tags]

        # Find other items with same tags
        related_items = (
            self.db.query(
                ItemTag.item_id,
                func.count(ItemTag.tag_id).label('shared_count'),
                func.group_concat(Tag.name).label('shared_tags')
            )
            .join(Tag, Tag.id == ItemTag.tag_id)
            .filter(
                ItemTag.tag_id.in_(tag_ids),
                ItemTag.item_id != item_id
            )
            .group_by(ItemTag.item_id)
            .all()
        )

        links = []
        for rel_item_id, shared_count, shared_tags_str in related_items:
            shared_tags = shared_tags_str.split(',') if shared_tags_str else []

            # Weight based on number of shared tags (normalized)
            weight = min(shared_count / 3.0, 1.0)

            explanation = f"Shares {shared_count} tag{'s' if shared_count > 1 else ''}: {', '.join(shared_tags[:2])}"

            links.append(ItemLinkData(
                source_id=item_id,
                target_id=rel_item_id,
                link_type="tag_match",
                weight=round(weight, 3),
                explanation=explanation[:200]
            ))

        return links

    async def _build_semantic_links(self, item_id: str, max_links: int = 5) -> List[ItemLinkData]:
        """
        Find semantically similar items using embeddings.
        Compares against items without existing semantic links to this item.
        """
        # Get source embedding
        source_emb = (
            self.db.query(ItemEmbedding)
            .filter(ItemEmbedding.item_id == item_id)
            .first()
        )

        if not source_emb:
            return []

        source_vector = json.loads(source_emb.embedding_json)

        # Get candidates (items with embeddings, excluding self and existing semantic links)
        existing_targets = (
            self.db.query(ItemLink.target_item_id)
            .filter(
                ItemLink.source_item_id == item_id,
                ItemLink.link_type == "semantic"
            )
            .union(
                self.db.query(ItemLink.source_item_id)
                .filter(
                    ItemLink.target_item_id == item_id,
                    ItemLink.link_type == "semantic"
                )
            )
            .subquery()
        )

        candidates = (
            self.db.query(
                ItemEmbedding.item_id,
                ItemEmbedding.embedding_json,
                Entry.text
            )
            .join(Entry, Entry.id == ItemEmbedding.item_id)
            .filter(
                ItemEmbedding.item_id != item_id,
                ~ItemEmbedding.item_id.in_(existing_targets.select())
            )
            .all()
        )

        if not candidates:
            return []

        # Calculate similarities
        similarities = []
        for cand_id, cand_emb_json, cand_text in candidates:
            try:
                cand_vector = json.loads(cand_emb_json)
                similarity = self.embedding_manager.cosine_similarity(source_vector, cand_vector)

                # Only consider reasonably similar items
                if similarity > 0.5:
                    similarities.append((cand_id, similarity, cand_text))
            except (json.JSONDecodeError, TypeError):
                continue

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        links = []
        for cand_id, similarity, cand_text in similarities[:max_links]:
            weight = round(min(similarity, 1.0), 3)

            # Generate brief explanation
            explanation = f"Semantic similarity: {int(similarity * 100)}% content overlap"

            links.append(ItemLinkData(
                source_id=item_id,
                target_id=cand_id,
                link_type="semantic",
                weight=weight,
                explanation=explanation[:200]
            ))

        return links


class SecondBrainRetriever:
    """Retrieves connected knowledge for AI personalization."""

    def __init__(self, db: Session, embedding_manager: EmbeddingManager):
        self.db = db
        self.embedding_manager = embedding_manager

    async def get_context(
        self,
        query_text: str,
        current_item_id: Optional[str] = None,
        top_k: int = 8,
        token_budget: int = 800
    ) -> Dict[str, Any]:
        """
        Get Second Brain context for a query.

        Returns:
            {
                "items": List[RelatedItem],  # Top related items
                "themes": Dict[str, List[str]],  # Grouped by theme/tag
                "summary": str,  # Brief summary for prompt injection
                "token_estimate": int
            }
        """
        # Generate query embedding
        query_embedding = await self.embedding_manager.generate_embedding(query_text)

        # Find related items via multiple strategies
        related_items = []

        # Strategy 1: Items linked to current item (if provided)
        if current_item_id:
            linked_items = self._get_linked_items(current_item_id)
            related_items.extend(linked_items)

        # Strategy 2: Items matching query semantically (if embedding worked)
        if query_embedding:
            semantic_items = await self._get_semantic_matches(query_embedding, current_item_id, limit=top_k)
            related_items.extend(semantic_items)

        # Strategy 3: Items with tag overlap to query keywords
        keyword_items = self._get_keyword_matches(query_text, current_item_id)
        related_items.extend(keyword_items)

        # Deduplicate and score
        deduplicated = self._deduplicate_and_score(related_items)

        # Take top K
        top_items = deduplicated[:top_k]

        # Group by themes for the AI
        themes = self._group_by_themes(top_items)

        # Create summary for prompt injection (token-aware)
        summary = self._create_context_summary(top_items, token_budget)

        return {
            "items": [self._item_to_dict(i) for i in top_items],
            "themes": themes,
            "summary": summary,
            "token_estimate": self._estimate_tokens(summary)
        }

    def _get_linked_items(self, item_id: str) -> List[RelatedItem]:
        """Get items directly linked to the given item."""
        # Query from both directions
        links = (
            self.db.query(
                ItemLink.target_item_id.label('connected_id'),
                ItemLink.link_type,
                ItemLink.weight,
                ItemLink.explanation
            )
            .filter(ItemLink.source_item_id == item_id)
            .all()
        )

        links += (
            self.db.query(
                ItemLink.source_item_id.label('connected_id'),
                ItemLink.link_type,
                ItemLink.weight,
                ItemLink.explanation
            )
            .filter(ItemLink.target_item_id == item_id)
            .all()
        )

        if not links:
            return []

        # Get entry details
        connected_ids = [l.connected_id for l in links]
        entries = (
            self.db.query(Entry)
            .filter(Entry.id.in_(connected_ids))
            .all()
        )
        entry_map = {e.id: e for e in entries}

        # Get shared tags for each
        related = []
        for link in links:
            entry = entry_map.get(link.connected_id)
            if not entry:
                continue

            shared_tags = self._get_shared_tags(item_id, link.connected_id)

            related.append(RelatedItem(
                item_id=link.connected_id,
                item_type=entry.feature_type,
                content_preview=entry.text[:150] + "..." if len(entry.text) > 150 else entry.text,
                relevance_score=link.weight,
                connection_type=link.link_type,
                shared_tags=shared_tags,
                explanation=link.explanation or "Connected in knowledge graph"
            ))

        return related

    async def _get_semantic_matches(
        self,
        query_vector: List[float],
        exclude_item_id: Optional[str],
        limit: int = 5
    ) -> List[RelatedItem]:
        """Find semantically similar items using cosine similarity."""
        candidates = (
            self.db.query(ItemEmbedding, Entry)
            .join(Entry, Entry.id == ItemEmbedding.item_id)
            .filter(
                ItemEmbedding.item_id != exclude_item_id if exclude_item_id else True,
                ItemEmbedding.embedding_json.isnot(None)
            )
            .all()
        )

        if not candidates:
            return []

        scored = []
        for emb, entry in candidates:
            try:
                vector = json.loads(emb.embedding_json)
                similarity = self.embedding_manager.cosine_similarity(query_vector, vector)

                if similarity > 0.6:  # Threshold for relevance
                    shared_tags = self._get_item_tags(entry.id)

                    scored.append(RelatedItem(
                        item_id=entry.id,
                        item_type=entry.feature_type,
                        content_preview=entry.text[:150] + "..." if len(entry.text) > 150 else entry.text,
                        relevance_score=round(similarity, 3),
                        connection_type="semantic_similarity",
                        shared_tags=shared_tags,
                        explanation=f"{int(similarity * 100)}% semantic similarity to query"
                    ))
            except (json.JSONDecodeError, TypeError):
                continue

        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored[:limit]

    def _get_keyword_matches(self, query_text: str, exclude_item_id: Optional[str]) -> List[RelatedItem]:
        """Find items with tag overlap to query keywords."""
        # Extract keywords from query
        keywords = [w.lower() for w in query_text.split() if len(w) > 3]

        if not keywords:
            return []

        # Find tags matching keywords
        matching_tags = (
            self.db.query(Tag.id, Tag.name)
            .filter(
                or_(*[Tag.name.ilike(f"%{kw}%") for kw in keywords])
            )
            .all()
        )

        if not matching_tags:
            return []

        tag_ids = [t[0] for t in matching_tags]

        # Find items with those tags
        items_with_tags = (
            self.db.query(
                ItemTag.item_id,
                func.count(ItemTag.tag_id).label('match_count'),
                func.group_concat(Tag.name).label('matched_tags')
            )
            .join(Tag, Tag.id == ItemTag.tag_id)
            .filter(
                ItemTag.tag_id.in_(tag_ids),
                ItemTag.item_id != exclude_item_id if exclude_item_id else True
            )
            .group_by(ItemTag.item_id)
            .having(func.count(ItemTag.tag_id) >= 1)
            .all()
        )

        if not items_with_tags:
            return []

        # Get entry details
        item_ids = [i[0] for i in items_with_tags]
        entries = (
            self.db.query(Entry)
            .filter(Entry.id.in_(item_ids))
            .all()
        )
        entry_map = {e.id: e for e in entries}

        related = []
        for item_id, match_count, matched_tags in items_with_tags:
            entry = entry_map.get(item_id)
            if not entry:
                continue

            weight = min(match_count / 2.0, 0.9)

            related.append(RelatedItem(
                item_id=item_id,
                item_type=entry.feature_type,
                content_preview=entry.text[:150] + "..." if len(entry.text) > 150 else entry.text,
                relevance_score=round(weight, 3),
                connection_type="shared_tag",
                shared_tags=matched_tags.split(',') if matched_tags else [],
                explanation=f"Matches {match_count} query keyword{'s' if match_count > 1 else ''}"
            ))

        return related

    def _get_shared_tags(self, item1_id: str, item2_id: str) -> List[str]:
        """Get tags shared between two items."""
        tags1 = (
            self.db.query(Tag.name)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .filter(ItemTag.item_id == item1_id)
            .all()
        )
        tags2 = (
            self.db.query(Tag.name)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .filter(ItemTag.item_id == item2_id)
            .all()
        )

        set1 = set(t[0] for t in tags1)
        set2 = set(t[0] for t in tags2)

        return list(set1 & set2)

    def _get_item_tags(self, item_id: str) -> List[str]:
        """Get all tags for an item."""
        tags = (
            self.db.query(Tag.name)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .filter(ItemTag.item_id == item_id)
            .all()
        )
        return [t[0] for t in tags]

    def _deduplicate_and_score(self, items: List[RelatedItem]) -> List[RelatedItem]:
        """Deduplicate items, keeping highest relevance score."""
        seen = {}
        for item in items:
            if item.item_id in seen:
                existing = seen[item.item_id]
                
                # Determine merged connection type
                new_type = existing.connection_type
                if item.connection_type != existing.connection_type:
                    new_type = "both"
                elif item.connection_type == "both" or existing.connection_type == "both":
                    new_type = "both"
                
                # Update if new item has higher score
                if item.relevance_score > existing.relevance_score:
                    seen[item.item_id] = item
                    item.connection_type = new_type
                else:
                    existing.connection_type = new_type
                    
            else:
                seen[item.item_id] = item

        result = list(seen.values())
        result.sort(key=lambda x: x.relevance_score, reverse=True)
        return result

    def _group_by_themes(self, items: List[RelatedItem]) -> Dict[str, List[str]]:
        """Group items by shared themes/tags."""
        themes = defaultdict(list)

        for item in items:
            for tag in item.shared_tags[:3]:  # Top 3 tags per item
                themes[tag].append(item.item_id)

        # Remove duplicates within themes and limit
        result = {}
        for theme, ids in themes.items():
            unique_ids = list(dict.fromkeys(ids))  # Preserve order, dedupe
            if len(unique_ids) >= 2:  # Only include themes with 2+ items
                result[theme] = unique_ids[:5]  # Max 5 items per theme

        return dict(result)

    def _create_context_summary(self, items: List[RelatedItem], token_budget: int) -> str:
        """Create a token-aware summary for prompt injection."""
        if not items:
            return ""

        parts = ["User's relevant past context:"]
        used_tokens = 10  # Approximate overhead

        for item in items[:6]:  # Max 6 items in context
            # Estimate tokens (rough: 4 chars ~= 1 token)
            preview = item.content_preview[:100]
            item_text = f"\n- [{item.item_type}] {preview}"
            item_tokens = len(item_text) // 4

            if used_tokens + item_tokens > token_budget:
                break

            parts.append(item_text)
            used_tokens += item_tokens

        if len(parts) == 1:  # Only header, no items fit
            return ""

        return "".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    def _item_to_dict(self, item: RelatedItem) -> Dict[str, Any]:
        """Convert RelatedItem to dict for JSON serialization."""
        return {
            "item_id": item.item_id,
            "item_type": item.item_type,
            "content_preview": item.content_preview,
            "relevance_score": item.relevance_score,
            "connection_type": item.connection_type,
            "shared_tags": item.shared_tags,
            "explanation": item.explanation
        }


# =============================================================================
# ORCHESTRATION SERVICE
# =============================================================================

class SecondBrainService:
    """
    Main service for Second Brain operations.
    Handles: tagging, embedding, linking, and retrieval.
    """

    def __init__(self, db: Session, ollama: OllamaConnector, embed_model: str = "mxbai-embed-large:latest", chat_model: Optional[str] = None):
        self.db = db
        self.ollama = ollama
        self.embed_model = embed_model
        self.chat_model = chat_model

        self.tag_generator = TagGenerator(ollama, chat_model)
        self.embedding_manager = EmbeddingManager(ollama, embed_model)
        self.link_builder = LinkBuilder(db, self.embedding_manager, ollama)
        self.retriever = SecondBrainRetriever(db, self.embedding_manager)

    async def process_new_item(
        self,
        item_id: str,
        content: str,
        item_type: str = "note",
        skip_embedding: bool = False,
        skip_linking: bool = False
    ) -> Dict[str, Any]:
        """
        Process a new item through the full Second Brain pipeline.
        Returns processing results for logging/metrics.
        """
        result = {
            "item_id": item_id,
            "tags_created": 0,
            "embedding_updated": False,
            "links_created": 0,
            "errors": []
        }

        try:
            # Step 1: Generate and store tags
            tags = await self.tag_generator.generate_tags(content)
            self._store_tags(item_id, tags)
            result["tags_created"] = len(tags)

            # Step 2: Generate and store embedding
            if not skip_embedding:
                embedding = await self.embedding_manager.generate_embedding(content)
                if embedding:
                    self._store_embedding(item_id, embedding)
                    result["embedding_updated"] = True
                else:
                    result["errors"].append("embedding_generation_failed")

            # Step 3: Build knowledge graph links
            if not skip_linking:
                links = await self.link_builder.build_links_for_item(item_id)
                self._store_links(links)
                result["links_created"] = len(links)

            logger.info(f"Second Brain: processed item {item_id} with {result['tags_created']} tags, {result['links_created']} links")

        except Exception as e:
            logger.error(f"Second Brain processing failed for {item_id}: {e}")
            result["errors"].append(str(e))

        return result

    def _store_tags(self, item_id: str, tags: List[GeneratedTag]):
        """Store tags in database, normalizing and deduping."""
        # Clear existing tags for this item
        self.db.query(ItemTag).filter(ItemTag.item_id == item_id).delete()

        for generated_tag in tags:
            normalized = TagNormalizer.normalize(generated_tag.tag)

            # Get or create tag
            tag = self.db.query(Tag).filter(Tag.name == normalized).first()
            if not tag:
                tag = Tag(name=normalized)
                self.db.add(tag)
                self.db.flush()  # Get ID

            # Create association
            association = ItemTag(item_id=item_id, tag_id=tag.id)
            self.db.add(association)

        self.db.commit()

    def _store_embedding(self, item_id: str, embedding: List[float]):
        """Store or update embedding for an item."""
        existing = (
            self.db.query(ItemEmbedding)
            .filter(ItemEmbedding.item_id == item_id)
            .first()
        )

        if existing:
            existing.embedding_json = json.dumps(embedding)
            existing.embedding_model = self.embed_model
            existing.embedding_dim = len(embedding)
        else:
            emb = ItemEmbedding(
                item_id=item_id,
                embedding_json=json.dumps(embedding),
                embedding_model=self.embed_model,
                embedding_dim=len(embedding)
            )
            self.db.add(emb)

        self.db.commit()

    def _store_links(self, links: List[ItemLinkData]):
        """Store knowledge graph links."""
        for link in links:
            # Check for existing link
            existing = (
                self.db.query(ItemLink)
                .filter(
                    ItemLink.source_item_id == link.source_id,
                    ItemLink.target_item_id == link.target_id,
                    ItemLink.link_type == link.link_type
                )
                .first()
            )

            if existing:
                # Update weight if changed
                existing.weight = link.weight
                existing.explanation = link.explanation
            else:
                link_obj = ItemLink(
                    source_item_id=link.source_id,
                    target_item_id=link.target_id,
                    link_type=link.link_type,
                    weight=link.weight,
                    explanation=link.explanation
                )
                self.db.add(link_obj)

        self.db.commit()

    async def get_context_for_query(
        self,
        query_text: str,
        current_item_id: Optional[str] = None,
        top_k: int = 8,
        token_budget: int = 800
    ) -> Dict[str, Any]:
        """Public API: Get Second Brain context for AI personalization."""
        return await self.retriever.get_context(
            query_text=query_text,
            current_item_id=current_item_id,
            top_k=top_k,
            token_budget=token_budget
        )

    async def reprocess_item(self, item_id: str) -> Dict[str, Any]:
        """Re-process an existing item (useful for content updates)."""
        entry = self.db.query(Entry).filter(Entry.id == item_id).first()
        if not entry:
            return {"error": "Item not found"}

        # Clear existing tags and links (keep embedding history)
        self.db.query(ItemTag).filter(ItemTag.item_id == item_id).delete()
        self.db.query(ItemLink).filter(
            or_(
                ItemLink.source_item_id == item_id,
                ItemLink.target_item_id == item_id
            )
        ).delete()
        self.db.commit()

        # Re-process
        return await self.process_new_item(
            item_id=item_id,
            content=entry.text,
            item_type=entry.feature_type,
            skip_embedding=False,
            skip_linking=False
        )

    def delete_item(self, item_id: str):
        """Clean up all Second Brain data for a deleted item."""
        # Cascading deletes are set up in SQLAlchemy relationships,
        # but we ensure explicit cleanup for clarity
        self.db.query(ItemTag).filter(ItemTag.item_id == item_id).delete()
        self.db.query(ItemEmbedding).filter(ItemEmbedding.item_id == item_id).delete()
        self.db.query(ItemLink).filter(
            or_(
                ItemLink.source_item_id == item_id,
                ItemLink.target_item_id == item_id
            )
        ).delete()
        self.db.commit()

        logger.info(f"Second Brain: cleaned up item {item_id}")


# =============================================================================
# BACKGROUND PROCESSOR
# =============================================================================

class SecondBrainBackgroundProcessor:
    """
    Handles deferred/background processing for Second Brain.
    Integrates with the existing queue system.
    """

    def __init__(self, db_factory, ollama: OllamaConnector, embed_model: str = "mxbai-embed-large:latest"):
        self.db_factory = db_factory
        self.ollama = ollama
        self.embed_model = embed_model

    async def process_queue_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single item from the background queue.
        Expected item_data: {"item_id": str, "content": str, "item_type": str}
        """
        db = self.db_factory()
        try:
            service = SecondBrainService(db, self.ollama, self.embed_model)
            result = await service.process_new_item(
                item_id=item_data["item_id"],
                content=item_data["content"],
                item_type=item_data.get("item_type", "note"),
                skip_embedding=False,
                skip_linking=False
            )
            return result
        finally:
            db.close()

    async def batch_process(self, item_ids: List[str]) -> List[Dict[str, Any]]:
        """Batch re-process multiple items (useful for migrations)."""
        results = []
        for item_id in item_ids:
            db = self.db_factory()
            try:
                service = SecondBrainService(db, self.ollama, self.embed_model)
                result = await service.reprocess_item(item_id)
                results.append(result)
            finally:
                db.close()
        return results
