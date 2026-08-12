from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.generate_human_gold_dataset import generate_dataset
from src.matching.filters import filter_jobs
from src.models.schemas import JobProfile


ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> tuple[bytes, object]:
    content = path.read_bytes()
    return content, json.loads(content.decode("utf-8"))


def test_generator_creates_heterogeneous_frozen_candidate_split(tmp_path: Path) -> None:
    output = tmp_path / "human_gold"
    generate_dataset(output)

    _, candidates = _read(output / "candidates.json")
    _, manifest = _read(output / "split_manifest.json")

    assert len(candidates) == 30
    assert len({row["candidate_id"] for row in candidates}) == 30
    assert len({row["role_family"] for row in candidates}) >= 11
    assert all(row["synthetic"] is True for row in candidates)
    assert all(row["education"] and row["skills"] and row["text"] for row in candidates)
    assert all(row["evidence"]["strength"] in {"strong", "medium", "limited"} for row in candidates)
    assert all(row["evidence"]["items"] for row in candidates)

    splits = manifest["candidate_splits"]
    assert {name: len(ids) for name, ids in splits.items()} == {
        "train": 18,
        "validation": 6,
        "blind_test": 6,
    }
    flattened = [candidate for values in splits.values() for candidate in values]
    assert len(flattened) == len(set(flattened)) == 30
    assert set(flattened) == {row["candidate_id"] for row in candidates}
    assert manifest["seed"] == 20260812
    assert manifest["version"] == "human-gold-readiness-v1"
    assert manifest["counts"] == {
        "candidates": 30,
        "train": 18,
        "validation": 6,
        "blind_test": 6,
        "pairs": 750,
    }
    assert len(manifest["sha256_fingerprint"]) == 64


def test_annotation_tasks_use_25_of_current_eligible_jobs_without_leakage(tmp_path: Path) -> None:
    output = tmp_path / "human_gold"
    generate_dataset(output)
    _, tasks = _read(output / "annotation_tasks.json")
    _, manifest = _read(output / "split_manifest.json")

    jobs = [
        JobProfile.model_validate(row)
        for row in json.loads((ROOT / "data/real_jobs/jobs.json").read_text(encoding="utf-8"))
        if row["status"] == "active"
    ]
    eligible_ids = {job.job_id for job in filter_jobs(jobs)}
    pairs = {(row["candidate_id"], row["job_id"]) for row in tasks}
    assert len(tasks) == len(pairs) == 750
    assert {row["job_id"] for row in tasks} <= eligible_ids
    assert all(row["synthetic_candidate"] is True for row in tasks)
    assert all(row["human_gold"] is False for row in tasks)
    assert all(row["grade"] is None and row["rationale"] is None for row in tasks)
    assert all(sum(row["candidate_id"] == candidate for row in tasks) == 25 for candidate in manifest["all_candidate_ids"])
    split_for = {
        candidate: split
        for split, candidate_ids in manifest["candidate_splits"].items()
        for candidate in candidate_ids
    }
    assert all(row["split"] == split_for[row["candidate_id"]] for row in tasks)


def test_generation_is_byte_identical_and_fingerprint_is_verifiable(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_dataset(first)
    generate_dataset(second)

    names = ("candidates.json", "split_manifest.json", "annotation_tasks.json")
    assert all((first / name).read_bytes() == (second / name).read_bytes() for name in names)

    manifest = json.loads((first / "split_manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256()
    digest.update((first / "candidates.json").read_bytes())
    digest.update((first / "annotation_tasks.json").read_bytes())
    assert manifest["sha256_fingerprint"] == digest.hexdigest()
