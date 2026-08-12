from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.repositories import JobRepository
from src.retrieval import HashingEmbedder, VectorStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--output", default="data/faiss_index")
    args = parser.parse_args()
    jobs = JobRepository(args.db).list_jobs()
    texts = [" ".join([job.title, *job.responsibilities, *job.required_skills, *job.preferred_skills]) for job in jobs]
    store = VectorStore()
    store.build(HashingEmbedder().encode(texts), [job.job_id for job in jobs])
    store.save(args.output)
    print(f"indexed={len(jobs)} output={args.output}")


if __name__ == "__main__":
    main()
