import json
from pathlib import Path

from src.parsers.job_parser import parse_job


ROOT = Path(__file__).resolve().parents[2]


def test_real_jobs_are_official_and_parseable() -> None:
    jobs = json.loads((ROOT / "data" / "real_jobs" / "jobs.json").read_text(encoding="utf-8"))
    assert len(jobs) >= 30
    assert len({job["source_url"] for job in jobs}) == len(jobs)
    for record in jobs:
        profile = parse_job(record)
        assert profile.source_url.startswith("https://")
        assert "上海" in profile.location
        assert profile.checked_at == "2026-08-12"
        assert profile.source_evidence


def test_real_job_labels_cover_each_candidate_job_pair() -> None:
    jobs = json.loads((ROOT / "data" / "real_jobs" / "jobs.json").read_text(encoding="utf-8"))
    labels = json.loads((ROOT / "data" / "real_jobs" / "relevance_labels.json").read_text(encoding="utf-8"))
    expected = {(candidate, job["job_id"]) for candidate in ("eval_llm", "eval_mining", "eval_nlp") for job in jobs}
    actual = {(label["candidate_id"], label["job_id"]) for label in labels}
    assert actual == expected
    assert all(0 <= label["grade"] <= 3 for label in labels)
    assert all(label["rationale"] for label in labels)
