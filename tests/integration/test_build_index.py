from __future__ import annotations

import json
import sys

from scripts import build_index
from src.models.schemas import JobProfile
from src.repositories import JobRepository


def test_build_index_cli_records_actual_hashing_backend(tmp_path, monkeypatch, capsys) -> None:
    db_path = tmp_path / "app.db"
    output_path = tmp_path / "index"
    JobRepository(db_path).upsert_many(
        [
            JobProfile(
                job_id="job-1",
                company="测试公司",
                title="中文算法工程师",
                responsibilities=["训练中文检索模型"],
                required_skills=["Python"],
            )
        ]
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_index.py",
            "--db",
            str(db_path),
            "--output",
            str(output_path),
            "--backend",
            "hashing",
            "--model",
            "ignored-for-hashing",
            "--device",
            "cpu",
            "--batch-size",
            "4",
            "--max-length",
            "512",
        ],
    )

    build_index.main()

    metadata = json.loads((output_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["backend"] == "hashing"
    assert metadata["model"] == "local-hashing-v1"
    assert metadata["dimensions"] == 512
    assert metadata["count"] == 1
    output = capsys.readouterr().out
    assert "backend=hashing" in output
    assert "model=local-hashing-v1" in output
    assert "dimensions=512" in output

