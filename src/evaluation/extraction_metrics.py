from __future__ import annotations


def precision_recall_f1(predicted: set[str] | list[str], expected: set[str] | list[str]) -> dict[str, float]:
    pred, gold = set(predicted), set(expected)
    true_positive = len(pred & gold)
    precision = true_positive / len(pred) if pred else (1.0 if not gold else 0.0)
    recall = true_positive / len(gold) if gold else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}
