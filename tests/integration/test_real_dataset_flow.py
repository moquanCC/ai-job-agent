from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.analysis_service import AnalysisService


ROOT = Path(__file__).resolve().parents[2]


def test_import_verified_jobs_reports_status_counts(tmp_path):
    service = AnalysisService(db_path=tmp_path / "app.db")

    count, statuses = service.import_verified_jobs(ROOT / "data/real_jobs/jobs.json")

    assert count == 30
    assert statuses == {"active": 27, "expired": 2, "unknown": 1}
    assert service.jobs.count() == 30


def test_import_verified_jobs_uses_repo_relative_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = AnalysisService(db_path=tmp_path / "app.db")

    count, statuses = service.import_verified_jobs()

    assert count == 30
    assert sum(statuses.values()) == 30


def test_import_verified_jobs_rejects_non_list_json(tmp_path):
    dataset = tmp_path / "jobs.json"
    dataset.write_text(json.dumps({"jobs": []}), encoding="utf-8")
    service = AnalysisService(db_path=tmp_path / "app.db")

    with pytest.raises(ValueError, match="列表"):
        service.import_verified_jobs(dataset)


def test_load_real_evaluation_preserves_disclosure(tmp_path):
    service = AnalysisService(db_path=tmp_path / "app.db")

    result = service.load_real_evaluation(ROOT / "data/real_jobs/evaluation_results.json")

    assert result["dataset"]["human_gold"] is False
    assert result["dataset"]["active_jobs"] == 27


@pytest.mark.parametrize("dataset", [{}, {"human_gold": True}, {"human_gold": 0}])
def test_load_real_evaluation_rejects_invalid_disclosure(tmp_path, dataset):
    result_path = tmp_path / "evaluation.json"
    result_path.write_text(json.dumps({"dataset": dataset}), encoding="utf-8")
    service = AnalysisService(db_path=tmp_path / "app.db")

    with pytest.raises(ValueError, match="评测披露字段"):
        service.load_real_evaluation(result_path)
