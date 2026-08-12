from __future__ import annotations

import pytest

from src.evaluation.fusion_tuning import (
    evaluate_weights,
    generate_weight_candidates,
    leave_one_candidate_out,
    passes_guardrails,
)


FIELDS = (
    "required_skill",
    "preferred_skill",
    "project",
    "semantic",
    "education",
    "location",
)


def _row(candidate: str, job: str, grade: int, **scores: float) -> dict:
    defaults = {
        "required_skill": 0.0,
        "preferred_skill": 0.0,
        "project": 0.0,
        "semantic": 0.0,
        "education": 0.0,
        "location": 100.0,
    }
    defaults.update(scores)
    return {
        "candidate_id": candidate,
        "job_id": job,
        "grade": grade,
        "subscores": defaults,
    }


def test_generate_weight_candidates_obeys_constrained_simplex() -> None:
    candidates = generate_weight_candidates(0.10)

    assert candidates
    assert candidates == generate_weight_candidates(0.10)
    for weights in candidates:
        assert tuple(weights) == FIELDS
        assert sum(weights.values()) == pytest.approx(1.0)
        assert weights["location"] == 0.0
        assert weights["required_skill"] >= 0.25
        assert 0.10 <= weights["semantic"] <= 0.35
        assert all(round(value / 0.10) == pytest.approx(value / 0.10) for value in weights.values())


@pytest.mark.parametrize("step", [0, -0.1, 0.3])
def test_generate_weight_candidates_rejects_invalid_step(step: float) -> None:
    with pytest.raises(ValueError, match="step"):
        generate_weight_candidates(step)


def test_evaluate_weights_ranks_cached_rows_and_uses_job_id_tie_break() -> None:
    rows = [
        _row("c1", "b", 0, required_skill=100),
        _row("c1", "a", 3, required_skill=100),
        _row("c1", "c", 2, required_skill=0),
    ]
    weights = {
        "required_skill": 1.0,
        "preferred_skill": 0.0,
        "project": 0.0,
        "semantic": 0.0,
        "education": 0.0,
        "location": 0.0,
    }

    result = evaluate_weights(rows, weights)

    assert result["by_candidate"]["c1"]["ranked_job_ids"] == ["a", "b", "c"]
    assert result["metrics"]["recall@5"] == 1.0
    assert result["metrics"]["recall@10"] == 1.0
    assert result["metrics"]["mrr"] == 1.0
    assert result["metrics"]["ndcg@5"] < 1.0
    assert result["metrics"]["ndcg@10"] < 1.0


def test_evaluate_weights_uses_production_fuse_rounding_before_job_id_tie_break() -> None:
    rows = [
        _row("c1", "z-higher-raw", 0, required_skill=50.0049),
        _row("c1", "a-lower-raw", 3, required_skill=50.0041),
    ]
    weights = {
        "required_skill": 1.0,
        "preferred_skill": 0.0,
        "project": 0.0,
        "semantic": 0.0,
        "education": 0.0,
        "location": 0.0,
    }

    result = evaluate_weights(rows, weights)

    assert result["by_candidate"]["c1"]["ranked_job_ids"] == [
        "a-lower-raw",
        "z-higher-raw",
    ]


def test_evaluate_weights_rejects_location_weight() -> None:
    rows = [_row("c", "j", 2)]
    weights = {field: 0.0 for field in FIELDS}
    weights["location"] = 0.1
    with pytest.raises(ValueError, match="location"):
        evaluate_weights(rows, weights)


def test_loco_is_deterministic_and_deployment_is_on_simplex() -> None:
    rows = []
    for candidate in ("c1", "c2", "c3"):
        rows.extend(
            [
                _row(candidate, "required", 3, required_skill=100),
                _row(candidate, "semantic", 2, semantic=100),
                _row(candidate, "noise", 0, preferred_skill=100),
            ]
        )
    candidates = generate_weight_candidates(0.10)

    result = leave_one_candidate_out(rows, candidates)

    assert [fold["held_out_candidate"] for fold in result["folds"]] == ["c1", "c2", "c3"]
    assert result == leave_one_candidate_out(rows, candidates)
    deployment = result["deployment_candidate"]
    assert deployment["weights"] in candidates
    assert sum(deployment["weights"].values()) == pytest.approx(1.0)
    assert deployment["weights"]["location"] == 0.0
    assert deployment["validation_scope"] == "descriptive_only"
    assert deployment["median_vector"]["location"] == 0.0
    assert deployment["selection"] == "nearest_legal_candidate_to_fold_winner_median"
    assert result["winner_diagnostics"]["unique_winner_count"] >= 1
    assert all("selection_tie_count" in fold for fold in result["folds"])
    assert all("selected_l1_from_baseline" in fold for fold in result["folds"])
    assert set(result["mean_metrics"]) == {"recall@5", "recall@10", "mrr", "ndcg@5", "ndcg@10"}


def test_loco_tie_break_prefers_lower_baseline_distance_then_lexicographic() -> None:
    rows = [
        _row(candidate, "only", 3, required_skill=100, semantic=100)
        for candidate in ("a", "b", "c")
    ]
    near = {
        "required_skill": 0.4,
        "preferred_skill": 0.1,
        "project": 0.2,
        "semantic": 0.2,
        "education": 0.1,
        "location": 0.0,
    }
    far = {
        "required_skill": 0.5,
        "preferred_skill": 0.0,
        "project": 0.1,
        "semantic": 0.3,
        "education": 0.1,
        "location": 0.0,
    }

    result = leave_one_candidate_out(rows, [far, near])

    assert all(fold["selected_weights"] == near for fold in result["folds"])


def test_promotion_guardrails_always_reject_exploratory_model_labels() -> None:
    baseline = {
        "descriptive_metrics": {"ndcg@5": 0.70, "recall@5": 0.60, "recall@10": 0.80},
        "loco_mean_metrics": {"ndcg@5": 0.68},
    }
    passing = {
        "descriptive_metrics": {"ndcg@5": 0.705, "recall@5": 0.60, "recall@10": 0.78},
        "loco_mean_metrics": {"ndcg@5": 0.68},
    }
    passed, reasons = passes_guardrails(baseline, passing)
    assert passed is False
    assert reasons == ["exploratory_insufficient_candidates", "human_gold_false"]

    failing = {
        "descriptive_metrics": {"ndcg@5": 0.704, "recall@5": 0.59, "recall@10": 0.779},
        "loco_mean_metrics": {"ndcg@5": 0.679},
    }
    passed, reasons = passes_guardrails(baseline, failing)
    assert passed is False
    assert len(reasons) == 6
    assert "exploratory_insufficient_candidates" in reasons
    assert "human_gold_false" in reasons
    assert "descriptive_ndcg5_improvement_below_0.005" in reasons
    assert "descriptive_recall5_below_baseline" in reasons
    assert "descriptive_recall10_degradation_over_0.02" in reasons
    assert "loco_mean_ndcg5_below_baseline" in reasons
