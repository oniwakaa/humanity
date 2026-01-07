from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient(url="http://127.0.0.1:6333")
name = "test_col"
if not client.collection_exists(name):
    client.create_collection(name, vectors_config=VectorParams(size=4, distance=Distance.COSINE))
    client.upsert(name, [PointStruct(id=1, vector=[0.1, 0.1, 0.1, 0.1], payload={"text": "hi"})])

try:
    res = client.query_points(collection_name=name, query=[0.1, 0.1, 0.1, 0.1], limit=1)
    print(f"Result type: {type(res)}")
    print(f"Result: {res}")
    
    # Try .points
    if hasattr(res, 'points'):
        print(f"Has points: {len(res.points)}")
        print(f"Payload: {res.points[0].payload}")
except Exception as e:
    print(f"Query failed: {e}")
