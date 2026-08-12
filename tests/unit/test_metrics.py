import pytest

from src.evaluation import mrr, ndcg_at_k, precision_recall_f1, recall_at_k


def test_extraction_metrics():
    metrics = precision_recall_f1({"Python", "SQL"}, {"Python", "PyTorch"})
    assert metrics == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_ranking_metrics_hand_calculated():
    ranked = ["x", "b", "a"]
    relevant = {"a", "b"}
    assert recall_at_k(ranked, relevant, 2) == 0.5
    assert mrr(ranked, relevant) == 0.5
    assert ndcg_at_k(["b", "a"], {"a": 3, "b": 1}, 2) < 1
    assert ndcg_at_k(["a", "b"], {"a": 3, "b": 1}, 2) == pytest.approx(1)


def test_empty_labels_are_perfect_not_crashing():
    assert recall_at_k([], set(), 5) == 1
    assert ndcg_at_k([], {}, 5) == 1
