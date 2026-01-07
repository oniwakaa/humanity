from qdrant_client import QdrantClient
from settings.manager import SettingsManager

def inspect_vectors():
    settings = SettingsManager().get_config()
    client = QdrantClient(url=settings.qdrant.url)
    
    # Get a point
    res, _ = client.scroll(
        collection_name=settings.qdrant.collection_name,
        limit=1,
        with_vectors=True
    )
    
    if not res:
        print("No points found in collection.")
        return

    point = res[0]
    vec = point.vector
    print(f"Point ID: {point.id}")
    print(f"Vector Length: {len(vec) if vec else 0}")
    if vec:
        print(f"First 10 dims: {vec[:10]}")
        print(f"Is all zero? {all(v == 0 for v in vec)}")

if __name__ == "__main__":
    inspect_vectors()
