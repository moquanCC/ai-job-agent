from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import mrr, ndcg_at_k, recall_at_k
from src.matching.ranker import rank_jobs
from src.models.schemas import JobProfile
from src.parsers.resume_parser import parse_resume


REAL = ROOT / "data" / "real_jobs"
EVALUATION = ROOT / "data" / "evaluation"


def main() -> None:
    jobs = [JobProfile.model_validate(item) for item in json.loads((REAL / "jobs.json").read_text(encoding="utf-8"))]
    jobs = [job for job in jobs if job.status == "active"]
    resumes = json.loads((EVALUATION / "resumes.json").read_text(encoding="utf-8"))
    gold_rows = json.loads((REAL / "relevance_gold.json").read_text(encoding="utf-8"))
    gold: dict[str, dict[str, int]] = {}
    active_ids = {job.job_id for job in jobs}
    for row in gold_rows:
        if row["job_id"] in active_ids:
            gold.setdefault(row["candidate_id"], {})[row["job_id"]] = int(row["grade"])

    methods = {
        "keyword": {"required_skill": 0.8, "preferred_skill": 0.2, "project": 0, "semantic": 0, "education": 0, "location": 0},
        "semantic": {"required_skill": 0, "preferred_skill": 0, "project": 0, "semantic": 1, "education": 0, "location": 0},
        "rule_fusion": {"required_skill": 0.35, "preferred_skill": 0.1, "project": 0.15, "semantic": 0.2, "education": 0.1, "location": 0.1},
        "full": {"required_skill": 0.3, "preferred_skill": 0.1, "project": 0.2, "semantic": 0.2, "education": 0.1, "location": 0.1},
    }
    started = time.perf_counter()
    rows = {name: [] for name in methods}
    for item in resumes:
        profile = parse_resume(item["text"], item["candidate_id"])
        grades = gold[profile.candidate_id]
        relevant = {job_id for job_id, grade in grades.items() if grade >= 2}
        for name, weights in methods.items():
            ranked = rank_jobs(profile, jobs, top_k=len(jobs), custom_weights=weights)
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

    results = {
        "dataset": {
            "synthetic": False,
            "annotation": "adjudicated-model-panel-v1",
            "human_gold": False,
            "candidates": len(resumes),
            "active_jobs": len(jobs),
            "pairs": sum(len(values) for values in gold.values()),
            "relevance_threshold": 2,
        },
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "ranking": {name: {key: round(average(values, key), 4) for key in values[0]} for name, values in rows.items()},
        "parameters": {"semantic_backend": "HashingVectorizer char 2-4 grams, 512 dimensions", "methods": methods},
        "limitations": [
            "Both independent labels and adjudication were model-assisted; human validation remains required for publication-grade claims.",
            "Only three synthetic candidate profiles are evaluated.",
            "Expired and unknown-status jobs are excluded from ranking evaluation.",
        ],
    }
    (REAL / "evaluation_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
