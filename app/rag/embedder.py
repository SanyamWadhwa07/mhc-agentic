from app.config import settings

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False


class Embedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if _ST_AVAILABLE:
                cls._instance.model = SentenceTransformer(settings.embedding_model)
            else:
                cls._instance.model = None
        return cls._instance

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_one(self, text: str) -> list[float]:
        if self.model is None:
            raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()
