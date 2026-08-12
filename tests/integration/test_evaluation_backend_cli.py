from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "script",
    ["scripts/run_evaluation.py", "scripts/run_real_evaluation.py"],
)
def test_evaluation_cli_records_hashing_backend_without_model_download(
    tmp_path: Path, script: str
) -> None:
    output = tmp_path / (Path(script).stem + ".json")

    subprocess.run(
        [
            sys.executable,
            script,
            "--embedding-backend",
            "hashing",
            "--embedding-model",
            "unused-in-hashing-mode",
            "--embedding-device",
            "cpu",
            "--batch-size",
            "4",
            "--max-length",
            "512",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    embedding = result["parameters"]["embedding"]
    assert embedding == {
        "requested_backend": "hashing",
        "actual_backend": "hashing",
        "model": "local-hashing-v1",
        "dimensions": 512,
        "batch_size": 4,
        "max_length": 512,
        "fallback_occurred": False,
    }
    assert result["ranking"]


def test_ci_invokes_evaluations_with_explicit_hashing_backend() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python scripts/run_evaluation.py --embedding-backend hashing" in workflow
    assert "python scripts/run_real_evaluation.py --embedding-backend hashing" in workflow


def _fusion_search(path: Path, actual_backend: str = "hashing") -> None:
    path.write_text(
        json.dumps(
            {
                "embedding": {"actual_backend": actual_backend},
                "deployment_candidate": {
                    "weights": {
                        "required_skill": 0.4,
                        "preferred_skill": 0.1,
                        "project": 0.1,
                        "semantic": 0.3,
                        "education": 0.1,
                        "location": 0.0,
                    },
                    "validation_scope": "descriptive_only",
                },
                "guardrails": {
                    "passed": False,
                    "failures": [
                        "exploratory_insufficient_candidates",
                        "human_gold_false",
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_real_evaluation_adds_disclosed_exploratory_fusion_method(tmp_path: Path) -> None:
    search = tmp_path / "fusion.json"
    output = tmp_path / "evaluation.json"
    _fusion_search(search)

    subprocess.run(
        [
            sys.executable,
            "scripts/run_real_evaluation.py",
            "--embedding-backend",
            "hashing",
            "--fusion-search",
            str(search),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["dataset"]["active_jobs"] == 27
    assert result["dataset"]["eligible_jobs"] == 26
    assert result["dataset"]["pairs"] == 78
    assert "full_baseline" in result["ranking"]
    assert "exploratory_tuned" in result["ranking"]
    assert result["ranking"]["full_baseline"] == result["ranking"]["full"]
    disclosure = result["fusion_search"]
    assert disclosure["method"] == "exploratory_tuned"
    assert disclosure["validation_scope"] == "descriptive_only"
    assert disclosure["guardrails"]["passed"] is False
    assert disclosure["guardrails"]["failures"] == [
        "exploratory_insufficient_candidates",
        "human_gold_false",
    ]
    assert result["parameters"]["methods"]["exploratory_tuned"]["location"] == 0.0
    assert "optimized" not in json.dumps(result).lower()


def test_real_evaluation_rejects_fusion_search_backend_mismatch(tmp_path: Path) -> None:
    search = tmp_path / "fusion.json"
    output = tmp_path / "evaluation.json"
    _fusion_search(search, actual_backend="bge-m3")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_real_evaluation.py",
            "--embedding-backend",
            "hashing",
            "--fusion-search",
            str(search),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "backend" in (completed.stdout + completed.stderr).lower()
    assert not output.exists()
