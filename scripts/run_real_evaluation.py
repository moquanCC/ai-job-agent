from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import mrr, ndcg_at_k, recall_at_k
from src.matching.filters import filter_jobs
from src.matching.ranker import rank_jobs
from src.models.schemas import JobProfile
from src.parsers.resume_parser import parse_resume
from src.retrieval import create_embedder


REAL = ROOT / "data" / "real_jobs"
EVALUATION = ROOT / "data" / "evaluation"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate active official JDs with a selected embedding backend. "
            "Manual BGE example: --embedding-backend bge-m3 --embedding-model BAAI/bge-m3"
        )
    )
    parser.add_argument("--embedding-backend", choices=("hashing", "bge-m3", "auto"), default="hashing")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-device", default="")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument(
        "--fusion-search",
        type=Path,
        default=None,
        help="Optional exploratory fusion-search JSON; never treated as optimized weights.",
    )
    parser.add_argument("--output", type=Path, default=REAL / "evaluation_results.json")
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


def _load_fusion_search(path: Path) -> tuple[dict[str, float], dict]:
    try:
        search = json.loads(path.read_text(encoding="utf-8"))
        weights = search["deployment_candidate"]["weights"]
        actual_backend = search["embedding"]["actual_backend"]
        guardrails = search["guardrails"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"无效的 fusion search 文件：{path}") from exc

    required = {
        "required_skill",
        "preferred_skill",
        "project",
        "semantic",
        "education",
        "location",
    }
    if set(weights) != required:
        raise ValueError("fusion search 的 deployment_candidate.weights 字段不完整")
    normalized = {key: float(weights[key]) for key in required}
    if normalized["location"] != 0.0:
        raise ValueError("fusion search 的 location 权重必须为 0（地点是硬过滤）")
    if any(value < 0 for value in normalized.values()) or abs(sum(normalized.values()) - 1.0) > 1e-9:
        raise ValueError("fusion search 权重必须是非负且总和为 1.0")
    if guardrails.get("passed") is not False:
        raise ValueError("fusion search 必须明确声明 guardrails.passed=false，不能作为优化权重")
    failures = guardrails.get("failures")
    if not isinstance(failures, list) or not failures:
        raise ValueError("fusion search 必须保留 guardrails.failures")
    return normalized, {
        "source": str(path),
        "actual_backend": str(actual_backend),
        "method": "exploratory_tuned",
        "validation_scope": "descriptive_only",
        "guardrails": {"passed": False, "failures": failures},
    }


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    fusion_weights: dict[str, float] | None = None
    fusion_disclosure: dict | None = None
    if args.fusion_search is not None:
        fusion_weights, fusion_disclosure = _load_fusion_search(args.fusion_search)
    embedder = create_embedder(
        args.embedding_backend,
        model_name=args.embedding_model,
        device=args.embedding_device or None,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    all_jobs = [JobProfile.model_validate(item) for item in json.loads((REAL / "jobs.json").read_text(encoding="utf-8"))]
    active_jobs = [job for job in all_jobs if job.status == "active"]
    jobs = filter_jobs(active_jobs)
    available_resumes = json.loads((EVALUATION / "resumes.json").read_text(encoding="utf-8"))
    gold_rows = json.loads((REAL / "relevance_gold.json").read_text(encoding="utf-8"))
    gold: dict[str, dict[str, int]] = {}
    active_ids = {job.job_id for job in jobs}
    for row in gold_rows:
        if row["job_id"] in active_ids:
            gold.setdefault(row["candidate_id"], {})[row["job_id"]] = int(row["grade"])
    available_by_id = {item["candidate_id"]: item for item in available_resumes}
    missing_profiles = sorted(set(gold) - set(available_by_id))
    if missing_profiles:
        raise ValueError(f"裁决标签缺少候选人画像：{missing_profiles}")
    resumes = [available_by_id[candidate_id] for candidate_id in sorted(gold)]

    methods = {
        "keyword": {"required_skill": 0.8, "preferred_skill": 0.2, "project": 0, "semantic": 0, "education": 0, "location": 0},
        "semantic": {"required_skill": 0, "preferred_skill": 0, "project": 0, "semantic": 1, "education": 0, "location": 0},
        "rule_fusion": {"required_skill": 7 / 18, "preferred_skill": 1 / 9, "project": 1 / 6, "semantic": 2 / 9, "education": 1 / 9, "location": 0.0},
        "full": {"required_skill": 1 / 3, "preferred_skill": 1 / 9, "project": 2 / 9, "semantic": 2 / 9, "education": 1 / 9, "location": 0.0},
    }
    if fusion_weights is not None:
        methods["full_baseline"] = dict(methods["full"])
        methods["exploratory_tuned"] = fusion_weights
    started = time.perf_counter()
    rows = {name: [] for name in methods}
    for item in resumes:
        profile = parse_resume(item["text"], item["candidate_id"])
        grades = gold[profile.candidate_id]
        relevant = {job_id for job_id, grade in grades.items() if grade >= 2}
        for name, weights in methods.items():
            ranked = rank_jobs(profile, jobs, top_k=len(jobs), custom_weights=weights, embedder=embedder)
            ids = [result.job_id for result in ranked]
            rows[name].append(
                {
                    "recall@5": recall_at_k(ids, relevant, 5),
                    "recall@10": recall_at_k(ids, relevant, 10),
                    "mrr": mrr(ids, relevant),
                    "ndcg@5": ndcg_at_k(ids, grades, 5),
                    "ndcg@10": ndcg_at_k(ids, grades, 10),
                }
            )

    def average(values: list[dict], key: str) -> float:
        return sum(row[key] for row in values) / len(values)

    embedding_metadata = _embedding_metadata(embedder, args)
    if fusion_disclosure is not None:
        if fusion_disclosure["actual_backend"] != embedding_metadata["actual_backend"]:
            raise ValueError(
                "fusion search actual backend 与当前 actual backend 不一致："
                f"{fusion_disclosure['actual_backend']} != {embedding_metadata['actual_backend']}"
            )
        fusion_disclosure = {
            key: value for key, value in fusion_disclosure.items() if key != "actual_backend"
        }

    results = {
        "dataset": {
            "synthetic": False,
            "annotation": "adjudicated-model-panel-v1",
            "human_gold": False,
            "candidates": len(resumes),
            "active_jobs": len(active_jobs),
            "eligible_jobs": len(jobs),
            "pairs": sum(len(values) for values in gold.values()),
            "relevance_threshold": 2,
        },
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "ranking": {name: {key: round(average(values, key), 4) for key in values[0]} for name, values in rows.items()},
        "parameters": {"embedding": embedding_metadata, "methods": methods},
        "limitations": [
            "Both independent labels and adjudication were model-assisted; human validation remains required for publication-grade claims.",
            "Only three synthetic candidate profiles are evaluated.",
            "Expired and unknown-status jobs are excluded from ranking evaluation.",
        ],
    }
    if fusion_disclosure is not None:
        results["fusion_search"] = fusion_disclosure
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
