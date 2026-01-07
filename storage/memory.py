import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import uuid
import os
from pathlib import Path

class MemoryLayer:
    def __init__(self, persistence_path: str = "./data/chroma", collection_name: str = "journal_entries", embedding_dim: int = 1024):
        # Ensure directory exists
        Path(persistence_path).mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persistence_path)
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def check_health(self) -> bool:
        """Checks if Chroma is initialized."""
        try:
            self.client.heartbeat()
            return True
        except:
            return False

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Upserts chunks with embeddings. 
        chunks should ideally have 'entry_id', 'text', 'metadata'.
        """
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            # Prefer using deterministic ID if possible, else random
            point_id = chunk.get("chunk_id") or str(uuid.uuid4())
            ids.append(point_id)
            
            # Chroma expects 'document' as text. 
            # If 'text' is in chunk, use it. Else use empty string?
            # Or strict separation? Logic usually implies text is in chunk.
            text = chunk.get("text", "")
            documents.append(text)
            
            # Prepare metadata (flat dict usually preferred)
            # Remove complex nested objects if any, Chroma handles primitives well
            meta = chunk.copy()
            # Ensure all values are str, int, float, bool
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)) and v is not None:
                     clean_meta[k] = v
                else:
                     clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        if ids:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

    def search(self, query_vector: List[float], limit: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Simple search wrapper.
        filters: Optional dict representing Must conditions. 
                 e.g. {"feature_type": "journal"}
        """
        where = filters if filters else None
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where
        )
        
        # Unpack Chroma structure: 
        # {'ids': [['id1']], 'distances': [[0.1]], 'metadatas': [[{...}]], 'documents': [[...]]}
        
        output = []
        if results['ids'] and len(results['ids']) > 0:
            count = len(results['ids'][0])
            for i in range(count):
                item = results['metadatas'][0][i].copy()
                item['text'] = results['documents'][0][i]
                item['chunk_id'] = results['ids'][0][i]
                # Chroma returns 'distance', convert to score if needed or keep as distance
                item['_score'] = 1.0 - results['distances'][0][i] # Approximate similarity from distance
                output.append(item)
                
        return output

    def delete_entry(self, entry_id: str):
        """Deletes all chunks associated with an entry_id."""
        self.collection.delete(
            where={"entry_id": entry_id}
        )
