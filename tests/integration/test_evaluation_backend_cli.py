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
