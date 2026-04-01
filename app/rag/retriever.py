from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.rag.confidence import compute_rag_confidence

_embedder = None
_store = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def _get_store():
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


async def retrieve(domain: str, query: str, n_results: int = 3) -> dict:
    """Returns {'documents': [...], 'confidence': float, 'scores': [...]}"""
    # Generate English query from Hinglish (simple passthrough — 8B handles expansion in ReAct)
    embedding = _get_embedder().embed_one(query)

    results = _get_store().query(domain, embedding, n_results=n_results)

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    confidence = compute_rag_confidence(distances)
    similarities = [1 / (1 + d) for d in distances]

    return {
        "documents": documents,
        "confidence": confidence,
        "scores": similarities,
    }
