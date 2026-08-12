from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_human_gold_evaluation import select_and_evaluate
from src.evaluation.fusion_tuning import BASELINE_WEIGHTS, generate_weight_candidates


def _row(candidate: str, job: str, grade: int, required: float, semantic: float) -> dict:
    return {
        "candidate_id": candidate, "job_id": job, "grade": grade,
        "subscores": {"required_skill": required, "preferred_skill": 0.0, "project": 0.0,
                      "semantic": semantic, "education": 100.0, "location": 100.0},
    }


def test_selection_never_uses_blind_candidates_and_blind_is_reported_once():
    splits = {"train": ["train"], "validation": ["validation"], "blind_test": ["blind"]}
    rows = []
    for candidate in ("train", "validation", "blind"):
        rows += [_row(candidate, "j1", 3, 100, 0), _row(candidate, "j2", 0, 0, 100)]
    result = select_and_evaluate(rows, splits, generate_weight_candidates(0.1), BASELINE_WEIGHTS)
    assert set(result["selection_candidate_ids"]) == {"train", "validation"}
    assert set(result["blind_test_candidate_ids"]) == {"blind"}
    assert set(result["selection_candidate_ids"]).isdisjoint(result["blind_test_candidate_ids"])
    assert result["protocol"]["blind_evaluations"] == 1
    assert set(result["blind_test"]) >= {"baseline", "candidate", "candidate_ndcg@5_non_decrease_fraction"}


def test_cli_rejects_non_human_gold(tmp_path: Path):
    from scripts.run_human_gold_evaluation import main
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps({"human_gold": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="human_gold=true"):
        main(["--human-gold", str(gold), "--output", str(tmp_path / "out.json")])
