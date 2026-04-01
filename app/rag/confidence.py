import numpy as np


def compute_rag_confidence(distances: list[float]) -> float:
    """Convert ChromaDB L2 distances to similarity scores and return average."""
    if not distances:
        return 0.0
    # ChromaDB returns L2 distances; convert to similarity (0-1)
    similarities = [1 / (1 + d) for d in distances]
    return round(float(np.mean(similarities)), 3)
