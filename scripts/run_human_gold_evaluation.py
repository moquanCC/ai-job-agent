from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.fusion_tuning import BASELINE_WEIGHTS, WEIGHT_FIELDS, evaluate_weights, generate_weight_candidates
from src.matching.filters import filter_jobs
from src.matching.ranker import _job_text, _resume_text, raw_subscores
from src.matching.semantic_matcher import semantic_scores
from src.models.schemas import JobProfile
from src.parsers.resume_parser import parse_resume
from src.retrieval import create_embedder


def _weight_tuple(weights: dict[str, float]) -> tuple[float, ...]:
    return tuple(float(weights[field]) for field in WEIGHT_FIELDS)


def _l1(weights: dict[str, float]) -> float:
    return sum(abs(float(weights[field]) - BASELINE_WEIGHTS[field]) for field in WEIGHT_FIELDS)


def _key(result: dict, weights: dict[str, float]) -> tuple:
    per_candidate = [row["metrics"]["ndcg@5"] for row in result["by_candidate"].values()]
    return (-result["metrics"]["ndcg@5"], -min(per_candidate), _l1(weights), _weight_tuple(weights))


def select_and_evaluate(cached_rows: list[dict], splits: dict[str, list[str]], candidates: list[dict[str, float]], baseline_weights: dict[str, float]) -> dict:
    train_ids, validation_ids, blind_ids = map(set, (splits["train"], splits["validation"], splits["blind_test"]))
    if train_ids & validation_ids or train_ids & blind_ids or validation_ids & blind_ids:
        raise ValueError("候选人 split 存在泄漏")
    present = {str(row["candidate_id"]) for row in cached_rows}
    if present != train_ids | validation_ids | blind_ids:
        raise ValueError("缓存候选人与冻结 split 不一致")
    train = [row for row in cached_rows if row["candidate_id"] in train_ids]
    validation = [row for row in cached_rows if row["candidate_id"] in validation_ids]
    blind = [row for row in cached_rows if row["candidate_id"] in blind_ids]

    train_evaluations = [(weights, evaluate_weights(train, weights)) for weights in candidates]
    best_train_key = min(_key(result, weights)[:2] for weights, result in train_evaluations)
    train_shortlist = [(weights, result) for weights, result in train_evaluations if _key(result, weights)[:2] == best_train_key]
    validation_evaluations = [(weights, evaluate_weights(validation, weights)) for weights, _ in train_shortlist]
    selected, validation_result = min(validation_evaluations, key=lambda pair: _key(pair[1], pair[0]))

    baseline_blind = evaluate_weights(blind, baseline_weights)
    candidate_blind = evaluate_weights(blind, selected)
    baseline_by = baseline_blind["by_candidate"]
    candidate_by = candidate_blind["by_candidate"]
    non_decrease = sum(candidate_by[c]["metrics"]["ndcg@5"] >= baseline_by[c]["metrics"]["ndcg@5"] for c in sorted(blind_ids)) / len(blind_ids)
    return {
        "protocol": {"selection": "train shortlist by mean/worst nDCG@5; final selection on validation", "blind_evaluations": 1},
        "selection_candidate_ids": sorted(train_ids | validation_ids),
        "train_candidate_ids": sorted(train_ids),
        "validation_candidate_ids": sorted(validation_ids),
        "blind_test_candidate_ids": sorted(blind_ids),
        "train_shortlist_count": len(train_shortlist),
        "selected_weights": selected,
        "validation_metrics": validation_result["metrics"],
        "blind_test": {"baseline": baseline_blind["metrics"], "candidate": candidate_blind["metrics"], "candidate_ndcg@5_non_decrease_fraction": non_decrease},
    }


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select fusion weights without opening the frozen blind test during selection.")
    parser.add_argument("--human-gold", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, default=ROOT / "data/human_gold/candidates.json")
    parser.add_argument("--jobs", type=Path, default=ROOT / "data/real_jobs/jobs.json")
    parser.add_argument("--tasks", type=Path, default=ROOT / "data/human_gold/annotation_tasks.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/human_gold/split_manifest.json")
    parser.add_argument("--embedding-backend", choices=("hashing", "bge-m3", "auto"), default="hashing")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-device", default="")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--step", type=float, default=0.1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    gold = _load(args.human_gold)
    if gold.get("human_gold") is not True or gold.get("status") != "complete":
        raise ValueError("评测要求完整 human_gold=true 文件")
    manifest, tasks = _load(args.manifest), _load(args.tasks)
    if gold.get("split", {}).get("fingerprint") != manifest.get("sha256_fingerprint"):
        raise ValueError("human gold split fingerprint 与 manifest 不一致")
    expected_pairs = {(row["candidate_id"], row["job_id"]) for row in tasks}
    gold_pairs = {(row["candidate_id"], row["job_id"]) for row in gold.get("rows", [])}
    if len(tasks) != 750 or len(expected_pairs) != 750 or gold_pairs != expected_pairs or gold.get("pair_count") != 750:
        raise ValueError("human gold 必须完整覆盖冻结的 750 pairs")

    job_records = _load(args.jobs)
    active = [JobProfile.model_validate(row) for row in job_records if row["status"] == "active"]
    jobs_by_id = {job.job_id: job for job in filter_jobs(active)}
    selected_job_ids = set(manifest["selected_job_ids"])
    if not selected_job_ids <= jobs_by_id.keys():
        raise ValueError("manifest 含非 eligible JD")
    jobs = [jobs_by_id[job_id] for job_id in sorted(selected_job_ids)]
    grades = {(row["candidate_id"], row["job_id"]): int(row["grade"]) for row in gold["rows"]}
    embedder = create_embedder(args.embedding_backend, model_name=args.embedding_model, device=args.embedding_device or None, batch_size=args.batch_size, max_length=args.max_length)
    cached_rows = []
    for item in _load(args.candidates):
        profile = parse_resume(item["text"], item["candidate_id"])
        scores = semantic_scores(_resume_text(profile), [_job_text(job) for job in jobs], embedder)
        for job, semantic in zip(jobs, scores, strict=True):
            cached_rows.append({"candidate_id": profile.candidate_id, "job_id": job.job_id, "grade": grades[(profile.candidate_id, job.job_id)], "subscores": raw_subscores(profile, job, semantic)})
    evaluation = select_and_evaluate(cached_rows, manifest["candidate_splits"], generate_weight_candidates(args.step), BASELINE_WEIGHTS)
    result = {"human_gold": True, "split_fingerprint": manifest["sha256_fingerprint"], "dataset": manifest["counts"], "embedding": {"requested_backend": args.embedding_backend, "actual_backend": "hashing" if embedder.name == "local-hashing-v1" else "bge-m3", "model": embedder.name, "dimensions": getattr(embedder, "dimensions", None)}, "baseline_weights": BASELINE_WEIGHTS, **evaluation}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
