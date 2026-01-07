from qdrant_client import QdrantClient
print("QdrantClient imported.")
client = QdrantClient(url="http://127.0.0.1:6333")
print(f"Client type: {type(client)}")
print(f"Methods: {[m for m in dir(client) if 'search' in m]}")
