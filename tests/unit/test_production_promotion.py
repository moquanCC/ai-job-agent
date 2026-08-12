from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.evaluation.promotion_gate import evaluate_production_promotion


ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT = "sha256:frozen-split"


def _status(**overrides):
    value = {
        "status": "complete",
        "human_gold": True,
        "candidate_count": 30,
        "pair_count": 750,
        "split": {
            "fingerprint": FINGERPRINT,
            "train_candidates": [f"train-{index}" for index in range(18)],
            "validation_candidates": [f"validation-{index}" for index in range(6)],
            "blind_test_candidates": [f"blind-{index}" for index in range(6)],
        },
        "agreement": {"exact": 0.70, "quadratic_weighted_kappa": 0.60},
    }
    value.update(overrides)
    return value


def _evaluation(**overrides):
    value = {
        "split_fingerprint": FINGERPRINT,
        "blind_test": {
            "baseline": {"ndcg@5": 0.60, "recall@5": 0.50, "recall@10": 0.70},
            "candidate": {"ndcg@5": 0.62, "recall@5": 0.50, "recall@10": 0.69},
            "candidate_ndcg@5_non_decrease_fraction": 0.70,
        },
    }
    value.update(overrides)
    return value


def test_gate_passes_only_at_every_threshold() -> None:
    result = evaluate_production_promotion(_status(), _evaluation(), {"passed": True})

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["evidence"]["split_counts"] == {"train": 18, "validation": 6, "blind_test": 6}


@pytest.mark.parametrize(
    ("status", "evaluation", "audit", "code"),
    [
        (_status(human_gold=False), _evaluation(), {"passed": True}, "human_gold_required"),
        (_status(candidate_count=29), _evaluation(), {"passed": True}, "candidate_count_invalid"),
        (_status(pair_count=749), _evaluation(), {"passed": True}, "pair_count_invalid"),
        (_status(agreement={"exact": 0.69, "quadratic_weighted_kappa": 0.60}), _evaluation(), {"passed": True}, "exact_agreement_below_threshold"),
        (_status(agreement={"exact": 0.70, "quadratic_weighted_kappa": 0.59}), _evaluation(), {"passed": True}, "quadratic_kappa_below_threshold"),
        (_status(), _evaluation(split_fingerprint="different"), {"passed": True}, "split_fingerprint_mismatch"),
        (_status(), _evaluation(blind_test={"baseline": {"ndcg@5": .60, "recall@5": .50, "recall@10": .70}, "candidate": {"ndcg@5": .619, "recall@5": .50, "recall@10": .70}, "candidate_ndcg@5_non_decrease_fraction": .70}), {"passed": True}, "blind_ndcg5_gain_below_threshold"),
        (_status(), _evaluation(blind_test={"baseline": {"ndcg@5": .60, "recall@5": .50, "recall@10": .70}, "candidate": {"ndcg@5": .62, "recall@5": .49, "recall@10": .70}, "candidate_ndcg@5_non_decrease_fraction": .70}), {"passed": True}, "blind_recall5_regression"),
        (_status(), _evaluation(blind_test={"baseline": {"ndcg@5": .60, "recall@5": .50, "recall@10": .70}, "candidate": {"ndcg@5": .62, "recall@5": .50, "recall@10": .689}, "candidate_ndcg@5_non_decrease_fraction": .70}), {"passed": True}, "blind_recall10_regression"),
        (_status(), _evaluation(blind_test={"baseline": {"ndcg@5": .60, "recall@5": .50, "recall@10": .70}, "candidate": {"ndcg@5": .62, "recall@5": .50, "recall@10": .70}, "candidate_ndcg@5_non_decrease_fraction": .69}), {"passed": True}, "candidate_direction_stability_below_threshold"),
        (_status(), _evaluation(), {"passed": False}, "engineering_audit_failed"),
    ],
)
def test_gate_returns_machine_failure_codes(status, evaluation, audit, code) -> None:
    result = evaluate_production_promotion(status, evaluation, audit)

    assert result["passed"] is False
    assert code in result["failures"]


def test_gate_detects_wrong_split_counts_and_candidate_leakage() -> None:
    status = _status()
    status["split"]["blind_test_candidates"][0] = status["split"]["train_candidates"][0]

    result = evaluate_production_promotion(status, _evaluation(), {"passed": True})

    assert "split_leakage_detected" in result["failures"]
    assert result["evidence"]["split_counts"] == {"train": 18, "validation": 6, "blind_test": 6}


def test_gate_rejects_wrong_split_cardinality_without_leakage() -> None:
    status = _status()
    status["split"]["blind_test_candidates"].pop()

    result = evaluate_production_promotion(status, _evaluation(), {"passed": True})

    assert "split_counts_invalid" in result["failures"]


@pytest.mark.parametrize("content", [None, "", "{}"])
def test_cli_missing_blank_or_readiness_inputs_always_reject(tmp_path: Path, content: str | None) -> None:
    status_path = tmp_path / "status.json"
    if content is not None:
        status_path.write_text(content, encoding="utf-8")
    evaluation_path = tmp_path / "evaluation.json"
    audit_path = tmp_path / "audit.json"
    evaluation_path.write_text(json.dumps(_evaluation()), encoding="utf-8")
    audit_path.write_text(json.dumps({"passed": True}), encoding="utf-8")
    output = tmp_path / "gate.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_production_promotion.py",
            "--status",
            str(status_path),
            "--evaluation",
            str(evaluation_path),
            "--audit",
            str(audit_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] is False
    assert "human_labels_incomplete" in result["failures"]
    assert not (tmp_path / "scoring.yaml").exists()


def test_readiness_status_refuses_even_if_other_evidence_is_strong() -> None:
    result = evaluate_production_promotion(
        _status(status="template_not_completed", human_gold=False),
        _evaluation(),
        {"passed": True},
    )

    assert result["passed"] is False
    assert "human_labels_incomplete" in result["failures"]
    assert "human_gold_required" in result["failures"]


def test_cli_complete_evidence_emits_pass_but_never_writes_configuration(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    evaluation_path = tmp_path / "evaluation.json"
    audit_path = tmp_path / "audit.json"
    output = tmp_path / "gate.json"
    status_path.write_text(json.dumps(_status()), encoding="utf-8")
    evaluation_path.write_text(json.dumps(_evaluation()), encoding="utf-8")
    audit_path.write_text(json.dumps({"passed": True}), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_production_promotion.py",
            "--status",
            str(status_path),
            "--evaluation",
            str(evaluation_path),
            "--audit",
            str(audit_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0
    assert result["passed"] is True
    assert result["configuration_write_allowed"] is False
    assert not (tmp_path / "scoring.yaml").exists()
