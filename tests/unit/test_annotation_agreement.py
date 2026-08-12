from scripts.evaluate_annotation_agreement import average_ranks, metrics, pearson


def test_average_ranks_handles_ties() -> None:
    assert average_ranks([0, 0, 2, 3]) == [1.5, 1.5, 3.0, 4.0]


def test_agreement_metrics_for_identical_labels() -> None:
    result = metrics([0, 1, 2, 3], [0, 1, 2, 3])
    assert result["exact_agreement"] == 1
    assert result["linear_weighted_kappa"] == 1
    assert result["quadratic_weighted_kappa"] == 1
    assert result["spearman_rho"] == 1


def test_pearson_returns_zero_for_constant_input() -> None:
    assert pearson([1, 1], [1, 2]) == 0
