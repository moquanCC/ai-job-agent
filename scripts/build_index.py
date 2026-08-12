from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.repositories import JobRepository
from src.retrieval import VectorStore, create_embedder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--output", default="data/faiss_index")
    parser.add_argument("--backend", choices=("auto", "bge-m3", "hashing"), default="auto")
    parser.add_argument("--model", default="BAAI/bge-m3")
    parser.add_argument("--device", default="")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=1024)
    args = parser.parse_args()
    jobs = JobRepository(args.db).list_jobs()
    texts = [" ".join([job.title, *job.responsibilities, *job.required_skills, *job.preferred_skills]) for job in jobs]
    embedder = create_embedder(
        args.backend,
        model_name=args.model,
        device=args.device or None,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    vectors = embedder.encode(texts)
    actual_model = embedder.name
    actual_backend = "hashing" if actual_model == "local-hashing-v1" else "bge-m3"
    store = VectorStore()
    store.build(vectors, [job.job_id for job in jobs])
    store.save(
        args.output,
        metadata={
            "backend": actual_backend,
            "model": actual_model,
            "normalized": True,
        },
    )
    print(
        f"indexed={len(jobs)} output={args.output} backend={actual_backend} "
        f"model={actual_model} dimensions={store.vectors.shape[1]}"
    )


if __name__ == "__main__":
    main()
