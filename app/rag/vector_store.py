from app.config import settings

try:
    import chromadb
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False


class VectorStore:
    def __init__(self):
        if not _CHROMA_AVAILABLE:
            raise RuntimeError("chromadb not installed. Run: pip install chromadb")
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    def get_or_create_collection(self, domain: str):
        return self.client.get_or_create_collection(name=f"mhc_{domain}")

    def add(self, domain: str, ids: list, embeddings: list, documents: list, metadatas: list = None):
        col = self.get_or_create_collection(domain)
        col.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas or [{}] * len(ids)
        )

    def query(self, domain: str, query_embedding: list, n_results: int = 3):
        col = self.get_or_create_collection(domain)
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "distances", "metadatas"]
        )
        return results
