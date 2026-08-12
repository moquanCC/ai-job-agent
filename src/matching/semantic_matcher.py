from __future__ import annotations

import numpy as np

from src.retrieval.embeddings import HashingEmbedder


def semantic_similarity(left: str, right: str, embedder: HashingEmbedder | None = None) -> float:
    vectors = (embedder or HashingEmbedder()).encode([left, right])
    return float(np.clip(np.dot(vectors[0], vectors[1]) * 100, 0, 100))
