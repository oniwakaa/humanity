from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
import uuid

class MemoryLayer:
    def __init__(self, url: str, collection_name: str, embedding_dim: int = 1024):
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.ensure_collection()

    def check_health(self) -> bool:
        """Checks if Qdrant is reachable."""
        try:
            self.client.get_collections()
            return True
        except:
            return False

    def ensure_collection(self):
        """Creates the collection if it doesn't exist."""
        collections = self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
            )

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Upserts chunks with embeddings. 
        chunks should ideally have 'entry_id', 'text', 'metadata'.
        """
        points = []
        for chunk, vector in zip(chunks, embeddings):
            # Prefer using deterministic ID if possible, else random
            point_id = chunk.get("chunk_id") or str(uuid.uuid4())
            
            payload = chunk.copy()
            # Ensure payload is JSON serializable
            
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(self, query_vector: List[float], limit: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Simple search wrapper.
        filters: Optional dict representing Must conditions. 
                 e.g. {"feature_type": "journal"}
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = None
        if filters:
            conditions = []
            for key, val in filters.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=val))
                )
            query_filter = Filter(must=conditions)

        hits_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter
        )
        # Return merged payload + score
        results = []
        for hit in hits_response.points:
            item = hit.payload.copy()
            item["_score"] = hit.score
            results.append(item)
        return results

    def delete_entry(self, entry_id: str):
        """Deletes all chunks associated with an entry_id."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="entry_id",
                        match=MatchValue(value=entry_id)
                    )
                ]
            )
        )
