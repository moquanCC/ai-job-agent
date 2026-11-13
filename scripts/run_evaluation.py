from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import mrr, ndcg_at_k, precision_recall_f1, recall_at_k
from src.matching.ranker import rank_jobs
from src.models.schemas import JobProfile
from src.parsers.resume_parser import parse_resume
from src.retrieval import create_embedder

DATA = ROOT / "data" / "evaluation"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the synthetic evaluation with an auditable embedding backend."
    )
    parser.add_argument("--embedding-backend", choices=("hashing", "bge-m3", "auto"), default="hashing")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-device", default="")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--output", type=Path, default=DATA / "results.json")
    args = parser.parse_args(argv)
    if args.batch_size <= 0 or args.max_length <= 0:
        parser.error("--batch-size and --max-length must be positive")
    return args


def _embedding_metadata(embedder, args: argparse.Namespace) -> dict:
    model = embedder.name
    return {
        "requested_backend": args.embedding_backend,
        "actual_backend": "hashing" if model == "local-hashing-v1" else "bge-m3",
        "model": model,
        "dimensions": getattr(embedder, "dimensions", None),
        "batch_size": args.batch_size,
        "max_length": args.max_length,
        "fallback_occurred": bool(getattr(embedder, "fallback_occurred", False)),
    }


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    embedder = create_embedder(
        args.embedding_backend,
        model_name=args.embedding_model,
        device=args.embedding_device or None,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    if not (DATA / "jobs.json").exists():
        from scripts.generate_sample_data import main as generate
        generate()
    jobs = [JobProfile.model_validate(item) for item in json.loads((DATA / "jobs.json").read_text(encoding="utf-8"))]
    resumes = json.loads((DATA / "resumes.json").read_text(encoding="utf-8"))
    relevance = json.loads((DATA / "relevance.json").read_text(encoding="utf-8"))
    methods = {
        "keyword": {"required_skill": 0.8, "preferred_skill": 0.2, "project": 0, "semantic": 0, "education": 0, "location": 0},
        "semantic": {"required_skill": 0, "preferred_skill": 0, "project": 0, "semantic": 1, "education": 0, "location": 0},
        "keyword_semantic": {"required_skill": 0.5, "preferred_skill": 0, "project": 0, "semantic": 0.5, "education": 0, "location": 0},
        "rule_fusion": {"required_skill": 7 / 18, "preferred_skill": 1 / 9, "project": 1 / 6, "semantic": 2 / 9, "education": 1 / 9, "location": 0.0},
        "full": {"required_skill": 1 / 3, "preferred_skill": 1 / 9, "project": 2 / 9, "semantic": 2 / 9, "education": 1 / 9, "location": 0.0},
    }
    started = time.perf_counter()
    extraction = []
    method_rows = {name: [] for name in methods}
    per_candidate = {}
    for item in resumes:
        profile = parse_resume(item["text"], item["candidate_id"])
        extraction_metrics = precision_recall_f1(profile.skills, item["expected_skills"])
        extraction.append(extraction_metrics)
        per_candidate[profile.candidate_id] = {
            "extraction": extraction_metrics,
            "ranking": {},
        }
        grades = relevance[item["candidate_id"]]
        relevant = {job_id for job_id, grade in grades.items() if grade >= 2}
        for name, method_weights in methods.items():
            ranked = rank_jobs(profile, jobs, top_k=10, custom_weights=method_weights, embedder=embedder)
            ids = [result.job_id for result in ranked]
            metrics = {"recall@5": recall_at_k(ids, relevant, 5), "recall@10": recall_at_k(ids, relevant, 10), "mrr": mrr(ids, relevant), "ndcg@5": ndcg_at_k(ids, grades, 5), "ndcg@10": ndcg_at_k(ids, grades, 10)}
            method_rows[name].append(metrics)
            per_candidate[profile.candidate_id]["ranking"][name] = {
                key: round(value, 4) for key, value in metrics.items()
            }
    average = lambda rows, key: sum(row[key] for row in rows) / len(rows)
    results = {
        "dataset": {
            "synthetic": True,
            "resumes": len(resumes),
            "jobs": len(jobs),
            "pairs": len(resumes) * len(jobs),
            "relevant_pairs": sum(
                grade >= 2 for grades in relevance.values() for grade in grades.values()
            ),
            "relevance_threshold": 2,
        },
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "extraction": {key: round(average(extraction, key), 4) for key in ("precision", "recall", "f1")},
        "ranking": {name: {key: round(average(rows, key), 4) for key in rows[0]} for name, rows in method_rows.items()},
        "parameters": {"embedding": _embedding_metadata(embedder, args), "methods": methods},
        "per_candidate": per_candidate,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
