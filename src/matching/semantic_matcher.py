from __future__ import annotations

import numpy as np

from src.retrieval.embeddings import HashingEmbedder, TextEmbedder


def semantic_scores(
    query_text: str,
    document_texts: list[str],
    embedder: TextEmbedder,
) -> list[float]:
    """Return clipped cosine scores while encoding two batches at most."""

    if not document_texts:
        return []
    query_vectors = embedder.encode([query_text])
    document_vectors = embedder.encode(document_texts)
    if query_vectors.ndim != 2 or query_vectors.shape[0] != 1:
        raise ValueError("查询向量必须是单行二维数组")
    if document_vectors.ndim != 2 or document_vectors.shape[0] != len(document_texts):
        raise ValueError("岗位向量数量与岗位文本数量不一致")
    if query_vectors.shape[1] != document_vectors.shape[1]:
        raise ValueError("查询向量与岗位向量维度不一致")
    scores = np.clip(document_vectors @ query_vectors[0], 0.0, 1.0) * 100.0
    return [float(score) for score in scores]


def semantic_similarity(left: str, right: str, embedder: TextEmbedder | None = None) -> float:
    return semantic_scores(left, [right], embedder or HashingEmbedder())[0]
