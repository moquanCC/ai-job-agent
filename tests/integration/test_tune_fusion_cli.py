from __future__ import annotations

import json

import pytest

from scripts import tune_fusion_weights
from src.models.schemas import JobProfile, ResumeProfile


def test_hashing_tuning_cli_writes_auditable_result(tmp_path) -> None:
    output = tmp_path / "fusion-search.json"

    tune_fusion_weights.main(
        [
            "--embedding-backend",
            "hashing",
            "--step",
            "0.10",
            "--output",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert set(result) == {
        "dataset",
        "embedding",
        "search",
        "baseline",
        "loco",
        "deployment_candidate",
        "guardrails",
        "limitations",
    }
    assert result["dataset"]["human_gold"] is False
    assert result["dataset"]["candidates"] == 3
    assert result["dataset"]["active_jobs"] == 27
    assert result["dataset"]["eligible_jobs"] == 26
    assert len(result["dataset"]["eligible_job_ids"]) == 26
    assert result["embedding"]["requested_backend"] == "hashing"
    assert result["embedding"]["actual_backend"] == "hashing"
    assert result["embedding"]["fallback_occurred"] is False
    assert result["search"]["step"] == 0.1
    assert result["search"]["candidate_count"] > 0
    assert result["search"]["unique_rankings"] > 0
    assert result["search"]["ranking_tie_count"] >= 0
    assert "stable_across_all_folds" in result["search"]["fold_winner_stability"]
    assert result["search"]["grid_uses_cached_subscores"] is True
    assert result["search"]["tie_breakers"] == [
        "mean_ndcg@5",
        "worst_candidate_ndcg@5",
        "baseline_l1_distance",
        "lexicographic_weights",
    ]
    assert len(result["loco"]["folds"]) == 3
    assert {fold["held_out_candidate"] for fold in result["loco"]["folds"]} == {
        "eval_llm",
        "eval_mining",
        "eval_nlp",
    }
    assert result["deployment_candidate"]["metrics_scope"] == "descriptive_only"
    assert isinstance(result["guardrails"]["passed"], bool)
    assert isinstance(result["guardrails"]["failures"], list)
    assert result["guardrails"]["passed"] is False
    assert "exploratory_insufficient_candidates" in result["guardrails"]["failures"]
    assert "human_gold_false" in result["guardrails"]["failures"]


def test_promote_config_is_always_rejected_for_exploratory_dataset(tmp_path) -> None:
    with pytest.raises(ValueError, match="3 个合成候选人.*human_gold=false"):
        tune_fusion_weights.main(
            [
                "--embedding-backend",
                "hashing",
                "--step",
                "0.10",
                "--output",
                str(tmp_path / "result.json"),
                "--promote-config",
            ]
        )


def test_tuning_cache_uses_raw_components_not_rounded_match_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = {
        "required_skill": 33.333333333333336,
        "preferred_skill": 0.0,
        "project": 14.285714285714286,
        "semantic": 12.34567,
        "education": 100.0,
        "location": 100.0,
    }
    captured: list[dict[str, float]] = []

    def fake_raw(
        resume: ResumeProfile, job: JobProfile, semantic_score: float
    ) -> dict[str, float]:
        captured.append(marker.copy())
        return marker.copy()

    monkeypatch.setattr(tune_fusion_weights, "raw_subscores", fake_raw)
    rows, _ = tune_fusion_weights.extract_cached_rows(
        tune_fusion_weights.create_embedder("hashing")
    )

    assert captured
    assert rows[0]["subscores"] == marker
    assert rows[0]["subscores"]["required_skill"] != 33.33
