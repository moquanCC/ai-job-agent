from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.matching.filters import filter_jobs
from src.matching.ranker import _job_text, _resume_text, raw_subscores
from src.matching.semantic_matcher import semantic_scores
from src.models.schemas import JobProfile
from src.parsers.resume_parser import parse_resume
from src.retrieval import create_embedder


REAL = ROOT / "data" / "real_jobs"
EVALUATION = ROOT / "data" / "evaluation"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune fusion weights on cached score components.")
    parser.add_argument("--embedding-backend", choices=("hashing", "bge-m3", "auto"), default="hashing")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-device", default="")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--step", type=float, default=0.05)
    parser.add_argument("--output", type=Path, default=REAL / "fusion_weight_search_bge_m3.json")
    parser.add_argument("--promote-config", action="store_true")
    args = parser.parse_args(argv)
    if args.batch_size <= 0 or args.max_length <= 0:
        parser.error("--batch-size and --max-length must be positive")
    if not 0 < args.step <= 1:
        parser.error("--step must be in (0, 1]")
    return args


def extract_cached_rows(embedder: Any) -> tuple[list[dict], dict]:
    """Encode each resume and its full eligible job batch exactly once."""
    all_jobs = [
        JobProfile.model_validate(item)
        for item in json.loads((REAL / "jobs.json").read_text(encoding="utf-8"))
    ]
    active_jobs = [job for job in all_jobs if job.status == "active"]
    jobs = filter_jobs(active_jobs)
    available_resumes = json.loads((EVALUATION / "resumes.json").read_text(encoding="utf-8"))
    labels = json.loads((REAL / "relevance_gold.json").read_text(encoding="utf-8"))
    grades = {(row["candidate_id"], row["job_id"]): int(row["grade"]) for row in labels}
    labeled_candidate_ids = {row["candidate_id"] for row in labels}
    resumes = [
        item for item in available_resumes if item["candidate_id"] in labeled_candidate_ids
    ]
    cached_rows: list[dict] = []
    for item in resumes:
        profile = parse_resume(item["text"], item["candidate_id"])
        semantic = semantic_scores(
            _resume_text(profile),
            [_job_text(job) for job in jobs],
            embedder,
        )
        for job, semantic_score in zip(jobs, semantic, strict=True):
            cached_rows.append(
                {
                    "candidate_id": profile.candidate_id,
                    "job_id": job.job_id,
                    "grade": grades[(profile.candidate_id, job.job_id)],
                    "subscores": raw_subscores(
                        profile, job, semantic_score=semantic_score
                    ),
                }
            )
    return cached_rows, {
        "candidate_ids": [item["candidate_id"] for item in resumes],
        "active_jobs": len(active_jobs),
        "eligible_jobs": len(jobs),
        "eligible_job_ids": [job.job_id for job in jobs],
    }


def _actual_backend(embedder: Any) -> str:
    return "hashing" if embedder.name == "local-hashing-v1" else "bge-m3"


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.promote_config:
        raise ValueError(
            "--promote-config 已拒绝：仅 3 个合成候选人且 human_gold=false，"
            "探索性结果不足以更新默认配置"
        )
    from src.evaluation.fusion_tuning import (
        BASELINE_WEIGHTS,
        evaluate_weights,
        generate_weight_candidates,
        leave_one_candidate_out,
        passes_guardrails,
    )

    embedder = create_embedder(
        args.embedding_backend,
        model_name=args.embedding_model,
        device=args.embedding_device or None,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    cached_rows, dataset_info = extract_cached_rows(embedder)
    candidates = generate_weight_candidates(args.step)
    baseline = evaluate_weights(cached_rows, BASELINE_WEIGHTS)
    loco = leave_one_candidate_out(cached_rows, candidates)
    deployment = loco["deployment_candidate"]
    deployment_metrics = evaluate_weights(cached_rows, deployment["weights"])["metrics"]
    deployment = {**deployment, "metrics": deployment_metrics, "metrics_scope": "descriptive_only"}
    passed, failures = passes_guardrails(
        {
            "descriptive_metrics": baseline["metrics"],
            # With fixed baseline weights, each candidate is held out once, so the
            # overall candidate macro mean equals the mean of held-out fold metrics.
            "loco_mean_metrics": baseline["metrics"],
        },
        {
            "descriptive_metrics": deployment_metrics,
            "loco_mean_metrics": loco["mean_metrics"],
        },
    )
    ranking_signatures = {
        tuple(
            tuple(result["by_candidate"][candidate_id]["ranked_job_ids"])
            for candidate_id in sorted(result["by_candidate"])
        )
        for result in (evaluate_weights(cached_rows, weights) for weights in candidates)
    }
    fold_winners = {
        tuple(sorted(fold["selected_weights"].items())) for fold in loco["folds"]
    }
    actual_backend = _actual_backend(embedder)
    result = {
        "dataset": {
            "synthetic": False,
            "annotation": "adjudicated-model-panel-v1",
            "human_gold": False,
            "candidates": len(dataset_info["candidate_ids"]),
            "candidate_ids": dataset_info["candidate_ids"],
            "active_jobs": dataset_info["active_jobs"],
            "eligible_jobs": dataset_info["eligible_jobs"],
            "eligible_job_ids": dataset_info["eligible_job_ids"],
            "pairs": len(cached_rows),
        },
        "embedding": {
            "requested_backend": args.embedding_backend,
            "actual_backend": actual_backend,
            "model": embedder.name,
            "dimensions": getattr(embedder, "dimensions", None),
            "batch_size": args.batch_size,
            "max_length": args.max_length,
            "fallback_occurred": bool(getattr(embedder, "fallback_occurred", False)),
        },
        "search": {
            "step": args.step,
            "candidate_count": len(candidates),
            "unique_rankings": len(ranking_signatures),
            "ranking_tie_count": len(candidates) - len(ranking_signatures),
            "fold_winner_stability": {
                "unique_winners": len(fold_winners),
                "stable_across_all_folds": len(fold_winners) == 1,
            },
            "constraints": {
                "sum": 1.0,
                "required_skill_min": 0.25,
                "semantic_range": [0.10, 0.35],
                "location": 0.0,
            },
            "objective": "LOCO mean nDCG@5 with deterministic tie-breaks",
            "tie_breakers": [
                "mean_ndcg@5",
                "worst_candidate_ndcg@5",
                "baseline_l1_distance",
                "lexicographic_weights",
            ],
            "seed": None,
            "grid_uses_cached_subscores": True,
        },
        "baseline": baseline,
        "loco": loco,
        "deployment_candidate": deployment,
        "guardrails": {"passed": passed, "failures": failures},
        "limitations": [
            "Only three synthetic candidate profiles are available; uncertainty is high.",
            "Labels and adjudication are model-assisted and are not human gold.",
            "All-data deployment metrics are descriptive after tuning, not held-out performance.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
