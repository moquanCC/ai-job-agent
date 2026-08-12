from __future__ import annotations

from typing import Any


EXPECTED_SPLIT_COUNTS = {"train": 18, "validation": 6, "blind_test": 6}
EPSILON = 1e-12


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _split_members(split: dict[str, Any], name: str) -> list[str]:
    value = split.get(f"{name}_candidates", split.get(name, []))
    if isinstance(value, dict):
        value = value.get("candidate_ids", value.get("candidates", []))
    return list(value) if isinstance(value, list) else []


def evaluate_production_promotion(
    status: dict[str, Any] | None,
    evaluation: dict[str, Any] | None,
    engineering_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate every promotion condition without mutating configuration."""

    status = status if isinstance(status, dict) else {}
    evaluation = evaluation if isinstance(evaluation, dict) else {}
    engineering_audit = engineering_audit if isinstance(engineering_audit, dict) else {}
    failures: list[str] = []

    readiness = status.get("status")
    if readiness != "complete":
        failures.append("human_labels_incomplete")
    if status.get("human_gold") is not True:
        failures.append("human_gold_required")

    candidate_count = status.get("candidate_count")
    pair_count = status.get("pair_count")
    if candidate_count != 30:
        failures.append("candidate_count_invalid")
    if pair_count != 750:
        failures.append("pair_count_invalid")

    split = status.get("split") if isinstance(status.get("split"), dict) else {}
    split_members = {name: _split_members(split, name) for name in EXPECTED_SPLIT_COUNTS}
    split_counts = {name: len(values) for name, values in split_members.items()}
    if split_counts != EXPECTED_SPLIT_COUNTS:
        failures.append("split_counts_invalid")
    all_members = [candidate for values in split_members.values() for candidate in values]
    if len(all_members) != len(set(all_members)):
        failures.append("split_leakage_detected")

    status_fingerprint = split.get("fingerprint", status.get("split_fingerprint"))
    evaluation_fingerprint = evaluation.get("split_fingerprint")
    if not status_fingerprint or status_fingerprint != evaluation_fingerprint:
        failures.append("split_fingerprint_mismatch")

    agreement = status.get("agreement") if isinstance(status.get("agreement"), dict) else {}
    exact = _number(agreement.get("exact", agreement.get("exact_agreement")))
    kappa = _number(
        agreement.get("quadratic_weighted_kappa", agreement.get("quadratic_kappa"))
    )
    if exact is None or exact + EPSILON < 0.70:
        failures.append("exact_agreement_below_threshold")
    if kappa is None or kappa + EPSILON < 0.60:
        failures.append("quadratic_kappa_below_threshold")

    blind = evaluation.get("blind_test") if isinstance(evaluation.get("blind_test"), dict) else {}
    baseline = blind.get("baseline") if isinstance(blind.get("baseline"), dict) else {}
    candidate = blind.get("candidate") if isinstance(blind.get("candidate"), dict) else {}
    baseline_ndcg5 = _number(baseline.get("ndcg@5"))
    candidate_ndcg5 = _number(candidate.get("ndcg@5"))
    baseline_recall5 = _number(baseline.get("recall@5"))
    candidate_recall5 = _number(candidate.get("recall@5"))
    baseline_recall10 = _number(baseline.get("recall@10"))
    candidate_recall10 = _number(candidate.get("recall@10"))
    stability = _number(blind.get("candidate_ndcg@5_non_decrease_fraction"))

    ndcg5_gain = (
        candidate_ndcg5 - baseline_ndcg5
        if candidate_ndcg5 is not None and baseline_ndcg5 is not None
        else None
    )
    if ndcg5_gain is None or ndcg5_gain + EPSILON < 0.02:
        failures.append("blind_ndcg5_gain_below_threshold")
    if (
        baseline_recall5 is None
        or candidate_recall5 is None
        or candidate_recall5 + EPSILON < baseline_recall5
    ):
        failures.append("blind_recall5_regression")
    recall10_drop = (
        baseline_recall10 - candidate_recall10
        if baseline_recall10 is not None and candidate_recall10 is not None
        else None
    )
    if recall10_drop is None or recall10_drop > 0.01 + EPSILON:
        failures.append("blind_recall10_regression")
    if stability is None or stability + EPSILON < 0.70:
        failures.append("candidate_direction_stability_below_threshold")

    if engineering_audit.get("passed") is not True:
        failures.append("engineering_audit_failed")

    return {
        "passed": not failures,
        "failures": failures,
        "configuration_write_allowed": False,
        "evidence": {
            "readiness_status": readiness,
            "human_gold": status.get("human_gold") is True,
            "candidate_count": candidate_count,
            "pair_count": pair_count,
            "split_counts": split_counts,
            "split_fingerprint_match": bool(status_fingerprint)
            and status_fingerprint == evaluation_fingerprint,
            "exact_agreement": exact,
            "quadratic_weighted_kappa": kappa,
            "blind_ndcg5_gain": ndcg5_gain,
            "blind_recall5_change": (
                candidate_recall5 - baseline_recall5
                if candidate_recall5 is not None and baseline_recall5 is not None
                else None
            ),
            "blind_recall10_drop": recall10_drop,
            "candidate_ndcg5_non_decrease_fraction": stability,
            "engineering_audit_passed": engineering_audit.get("passed") is True,
        },
        "thresholds": {
            "candidates": 30,
            "pairs": 750,
            "split_counts": EXPECTED_SPLIT_COUNTS,
            "exact_agreement_min": 0.70,
            "quadratic_weighted_kappa_min": 0.60,
            "blind_ndcg5_gain_min": 0.02,
            "blind_recall5_min_change": 0.0,
            "blind_recall10_max_drop": 0.01,
            "candidate_ndcg5_non_decrease_fraction_min": 0.70,
        },
    }
