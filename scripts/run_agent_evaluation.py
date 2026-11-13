from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.agent_behavior import evaluate_job_agent, load_agent_scenarios
from src.models.schemas import JobProfile
from src.parsers.resume_parser import parse_resume
from src.retrieval.embeddings import create_embedder


def main() -> None:
    parser = argparse.ArgumentParser(description="运行求职决策 Agent 合成行为评测")
    parser.add_argument(
        "--scenarios",
        default=str(ROOT / "data" / "evaluation" / "agent_scenarios.json"),
    )
    parser.add_argument(
        "--resumes",
        default=str(ROOT / "data" / "evaluation" / "resumes.json"),
    )
    parser.add_argument(
        "--jobs",
        default=str(ROOT / "data" / "evaluation" / "jobs.json"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "evaluation" / "agent_results.json"),
    )
    parser.add_argument("--embedding-backend", choices=("hashing", "bge-m3"), default="hashing")
    args = parser.parse_args()

    resume_rows = json.loads(Path(args.resumes).read_text(encoding="utf-8"))
    resumes = {}
    for row in resume_rows:
        parsed = parse_resume(row["text"])
        resumes[row["candidate_id"]] = parsed.model_copy(
            update={"candidate_id": row["candidate_id"]}
        )
    jobs = [
        JobProfile.model_validate(row)
        for row in json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    ]
    embedder = create_embedder(args.embedding_backend)
    report = evaluate_job_agent(
        load_agent_scenarios(args.scenarios),
        resumes,
        jobs,
        embedder,
        requested_backend=args.embedding_backend,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
