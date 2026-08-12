from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from src.evaluation.ranking_metrics import mrr, ndcg_at_k, recall_at_k
from src.matching.score_fusion import fuse


WEIGHT_FIELDS = (
    "required_skill",
    "preferred_skill",
    "project",
    "semantic",
    "education",
    "location",
)
TUNABLE_FIELDS = WEIGHT_FIELDS[:-1]

# The current profile with location removed because Shanghai is a hard filter.
BASELINE_WEIGHTS = {
    "required_skill": 1 / 3,
    "preferred_skill": 1 / 9,
    "project": 2 / 9,
    "semantic": 2 / 9,
    "education": 1 / 9,
    "location": 0.0,
}
METRIC_FIELDS = ("recall@5", "recall@10", "mrr", "ndcg@5", "ndcg@10")
_EPSILON = 1e-12


def generate_weight_candidates(step: float) -> list[dict[str, float]]:
    """Enumerate the constrained integer simplex in deterministic order."""

    if not isinstance(step, (int, float)) or isinstance(step, bool) or step <= 0:
        raise ValueError("step 必须是正数")
    units_float = 1.0 / float(step)
    units = round(units_float)
    if units < 1 or abs(units_float - units) > 1e-9:
        raise ValueError("step 必须能整除 1.0")

    candidates: list[dict[str, float]] = []
    for required in range(units + 1):
        for preferred in range(units - required + 1):
            for project in range(units - required - preferred + 1):
                for semantic in range(units - required - preferred - project + 1):
                    education = units - required - preferred - project - semantic
                    required_value = required / units
                    semantic_value = semantic / units
                    if required_value + _EPSILON < 0.25:
                        continue
                    if not 0.10 - _EPSILON <= semantic_value <= 0.35 + _EPSILON:
                        continue
                    candidates.append(
                        {
                            "required_skill": required_value,
                            "preferred_skill": preferred / units,
                            "project": project / units,
                            "semantic": semantic_value,
                            "education": education / units,
                            "location": 0.0,
                        }
                    )
    return candidates


def _validate_weights(weights: dict[str, float]) -> None:
    missing = [field for field in WEIGHT_FIELDS if field not in weights]
    if missing:
        raise ValueError("权重缺少字段：" + ", ".join(missing))
    if abs(float(weights["location"])) > _EPSILON:
        raise ValueError("location 是硬过滤条件，权重必须为 0")
    if any(float(weights[field]) < 0 for field in WEIGHT_FIELDS):
        raise ValueError("权重不能为负数")
    if abs(sum(float(weights[field]) for field in WEIGHT_FIELDS) - 1.0) > 1e-9:
        raise ValueError("权重总和必须为 1.0")


def _row_subscore(row: dict[str, Any], field: str) -> float:
    source = row.get("subscores", row)
    if field not in source:
        raise ValueError(f"缓存行缺少评分字段：{field}")
    return float(source[field])


def evaluate_weights(cached_rows: list[dict], weights: dict[str, float]) -> dict:
    """Rank cached component rows and aggregate candidate-level metrics."""

    _validate_weights(weights)
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen_pairs: set[tuple[str, str]] = set()
    for row in cached_rows:
        candidate_id = str(row["candidate_id"])
        job_id = str(row["job_id"])
        pair = (candidate_id, job_id)
        if pair in seen_pairs:
            raise ValueError(f"缓存中存在重复候选人岗位对：{candidate_id}/{job_id}")
        seen_pairs.add(pair)
        grouped[candidate_id].append(row)

    by_candidate: dict[str, dict[str, Any]] = {}
    for candidate_id in sorted(grouped):
        scored: list[tuple[float, str, int]] = []
        grades: dict[str, int] = {}
        for row in grouped[candidate_id]:
            job_id = str(row["job_id"])
            grade = int(row["grade"])
            grades[job_id] = grade
            subscores = {
                field: _row_subscore(row, field) for field in WEIGHT_FIELDS
            }
            score = fuse(subscores, weights)
            scored.append((score, job_id, grade))
        scored.sort(key=lambda item: (-item[0], item[1]))
        ranked_ids = [job_id for _, job_id, _ in scored]
        relevant = {job_id for job_id, grade in grades.items() if grade >= 2}
        metrics = {
            "recall@5": recall_at_k(ranked_ids, relevant, 5),
            "recall@10": recall_at_k(ranked_ids, relevant, 10),
            "mrr": mrr(ranked_ids, relevant),
            "ndcg@5": ndcg_at_k(ranked_ids, grades, 5),
            "ndcg@10": ndcg_at_k(ranked_ids, grades, 10),
        }
        by_candidate[candidate_id] = {
            "ranked_job_ids": ranked_ids,
            "metrics": metrics,
        }

    aggregate = {
        metric: (
            sum(entry["metrics"][metric] for entry in by_candidate.values())
            / len(by_candidate)
            if by_candidate
            else 0.0
        )
        for metric in METRIC_FIELDS
    }
    return {
        "weights": {field: float(weights[field]) for field in WEIGHT_FIELDS},
        "metrics": aggregate,
        "by_candidate": by_candidate,
        "candidate_count": len(by_candidate),
    }


def _weight_tuple(weights: dict[str, float]) -> tuple[float, ...]:
    return tuple(float(weights[field]) for field in WEIGHT_FIELDS)


def _l1_from_baseline(weights: dict[str, float]) -> float:
    return sum(abs(float(weights[field]) - BASELINE_WEIGHTS[field]) for field in WEIGHT_FIELDS)


def _selection_key(evaluation: dict, weights: dict[str, float]) -> tuple:
    candidate_metrics = [
        entry["metrics"] for entry in evaluation["by_candidate"].values()
    ]
    worst_ndcg5 = min(metric["ndcg@5"] for metric in candidate_metrics)
    mean_metrics = evaluation["metrics"]
    return (
        -mean_metrics["ndcg@5"],
        -worst_ndcg5,
        _l1_from_baseline(weights),
        _weight_tuple(weights),
    )


def _project_median_to_candidates(
    winners: list[dict[str, float]], candidates: list[dict[str, float]]
) -> tuple[dict[str, float], dict[str, float]]:
    target = {
        field: float(median([winner[field] for winner in winners]))
        for field in WEIGHT_FIELDS
    }
    selected = min(
        candidates,
        key=lambda weights: (
            sum(abs(float(weights[field]) - target[field]) for field in WEIGHT_FIELDS),
            _weight_tuple(weights),
        ),
    )
    return target, selected


def leave_one_candidate_out(
    cached_rows: list[dict], candidates: list[dict[str, float]]
) -> dict:
    """Select on N-1 candidates and evaluate once on each held-out candidate."""

    candidate_ids = sorted({str(row["candidate_id"]) for row in cached_rows})
    if len(candidate_ids) < 2:
        raise ValueError("LOCO 至少需要两个候选人")
    if not candidates:
        raise ValueError("权重候选集合不能为空")
    for weights in candidates:
        _validate_weights(weights)

    folds: list[dict[str, Any]] = []
    winners: list[dict[str, float]] = []
    for held_out in candidate_ids:
        training_rows = [
            row for row in cached_rows if str(row["candidate_id"]) != held_out
        ]
        held_out_rows = [
            row for row in cached_rows if str(row["candidate_id"]) == held_out
        ]
        evaluated = [
            (weights, evaluate_weights(training_rows, weights)) for weights in candidates
        ]
        selected_weights, training_result = min(
            evaluated, key=lambda pair: _selection_key(pair[1], pair[0])
        )
        selected_key_without_lexical = _selection_key(
            training_result, selected_weights
        )[:-1]
        selection_tie_count = sum(
            _selection_key(result, weights)[:-1] == selected_key_without_lexical
            for weights, result in evaluated
        )
        unique_rankings = {
            tuple(
                (candidate_id, tuple(entry["ranked_job_ids"]))
                for candidate_id, entry in sorted(result["by_candidate"].items())
            )
            for _, result in evaluated
        }
        held_out_result = evaluate_weights(held_out_rows, selected_weights)
        winner = {field: float(selected_weights[field]) for field in WEIGHT_FIELDS}
        winners.append(winner)
        folds.append(
            {
                "held_out_candidate": held_out,
                "selected_weights": winner,
                "selected_l1_from_baseline": _l1_from_baseline(winner),
                "selection_tie_count": selection_tie_count,
                "unique_training_rankings": len(unique_rankings),
                "training_metrics": training_result["metrics"],
                "held_out_metrics": held_out_result["metrics"],
            }
        )

    mean_metrics = {
        metric: sum(fold["held_out_metrics"][metric] for fold in folds) / len(folds)
        for metric in METRIC_FIELDS
    }
    median_vector, deployment_weights = _project_median_to_candidates(winners, candidates)
    deployment_evaluation = evaluate_weights(cached_rows, deployment_weights)
    return {
        "folds": folds,
        "mean_metrics": mean_metrics,
        "deployment_candidate": {
            "weights": {
                field: float(deployment_weights[field]) for field in WEIGHT_FIELDS
            },
            "median_vector": median_vector,
            "selection": "nearest_legal_candidate_to_fold_winner_median",
            "l1_from_median": sum(
                abs(float(deployment_weights[field]) - median_vector[field])
                for field in WEIGHT_FIELDS
            ),
            "metrics": deployment_evaluation["metrics"],
            "validation_scope": "descriptive_only",
        },
        "winner_diagnostics": {
            "unique_winner_count": len({_weight_tuple(winner) for winner in winners}),
            "component_ranges": {
                field: {
                    "min": min(winner[field] for winner in winners),
                    "max": max(winner[field] for winner in winners),
                }
                for field in WEIGHT_FIELDS
            },
        },
    }


def _metric_group(result: dict, preferred_key: str) -> dict:
    if preferred_key in result:
        return result[preferred_key]
    if "metrics" in result:
        return result["metrics"]
    raise ValueError(f"结果缺少 {preferred_key}")


def passes_guardrails(baseline: dict, candidate: dict) -> tuple[bool, list[str]]:
    """Return promotion status and every failed guardrail, without short-circuiting."""

    baseline_full = _metric_group(baseline, "descriptive_metrics")
    candidate_full = _metric_group(candidate, "descriptive_metrics")
    baseline_loco = _metric_group(
        baseline.get("loco", baseline), "loco_mean_metrics"
    )
    candidate_loco = _metric_group(
        candidate.get("loco", candidate), "loco_mean_metrics"
    )

    reasons: list[str] = ["exploratory_insufficient_candidates", "human_gold_false"]
    ndcg5_gain = candidate_full["ndcg@5"] - baseline_full["ndcg@5"]
    if ndcg5_gain + _EPSILON < 0.005:
        reasons.append("descriptive_ndcg5_improvement_below_0.005")
    if candidate_full["recall@5"] + _EPSILON < baseline_full["recall@5"]:
        reasons.append("descriptive_recall5_below_baseline")
    if candidate_full["recall@10"] + _EPSILON < baseline_full["recall@10"] - 0.02:
        reasons.append("descriptive_recall10_degradation_over_0.02")
    if candidate_loco["ndcg@5"] + _EPSILON < baseline_loco["ndcg@5"]:
        reasons.append("loco_mean_ndcg5_below_baseline")
    return False, reasons
