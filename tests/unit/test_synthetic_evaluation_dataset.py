import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "evaluation"


def test_extended_synthetic_candidates_have_complete_labels():
    jobs = json.loads((DATA / "jobs.json").read_text(encoding="utf-8"))
    resumes = json.loads((DATA / "resumes.json").read_text(encoding="utf-8"))
    relevance = json.loads((DATA / "relevance.json").read_text(encoding="utf-8"))

    candidate_ids = {row["candidate_id"] for row in resumes}
    job_ids = {row["job_id"] for row in jobs}

    assert len(resumes) == 12
    assert len(candidate_ids) == 12
    assert set(relevance) == candidate_ids
    assert all(set(grades) == job_ids for grades in relevance.values())
    assert all(any(grade >= 2 for grade in grades.values()) for grades in relevance.values())
    assert all(row["expected_skills"] for row in resumes)
