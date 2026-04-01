import json
import hashlib
from pathlib import Path
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore

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

KNOWLEDGE_FILES = {
    "therapy": "app/knowledge/therapy_knowledge.json",
    "assessment": "app/knowledge/assessment_knowledge.json",
    "crisis": "app/knowledge/crisis_knowledge.json",
    "resource": "app/knowledge/resource_knowledge.json",
}


def ingest_all():
    for domain, path in KNOWLEDGE_FILES.items():
        p = Path(path)
        if not p.exists():
            print(f"Skipping {domain} — file not found: {path}")
            continue

        with open(p) as f:
            chunks = json.load(f)

        ids, embeddings, documents, metadatas = [], [], [], []

        for chunk in chunks:
            text = chunk.get("text", chunk) if isinstance(chunk, dict) else chunk
            doc_id = hashlib.md5(text.encode()).hexdigest()
            embedding = _get_embedder().embed_one(text)

            ids.append(doc_id)
            embeddings.append(embedding)
            documents.append(text)
            metadatas.append({"domain": domain, "source": path})

        if ids:
            _get_store().add(domain, ids, embeddings, documents, metadatas)
            print(f"Ingested {len(ids)} chunks for domain: {domain}")


if __name__ == "__main__":
    ingest_all()
