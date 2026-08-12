from __future__ import annotations

import math


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 1.0
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)


def mrr(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    for index, item in enumerate(ranked_ids, 1):
        if item in relevant_ids:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int | float], k: int) -> float:
    def dcg(values: list[float]) -> float:
        return sum((2**value - 1) / math.log2(index + 2) for index, value in enumerate(values))

    actual = [float(relevance.get(item, 0)) for item in ranked_ids[:k]]
    ideal = sorted((float(value) for value in relevance.values()), reverse=True)[:k]
    denominator = dcg(ideal)
    return dcg(actual) / denominator if denominator else 1.0
