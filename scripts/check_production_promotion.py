from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.promotion_gate import evaluate_production_promotion


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read human-gold evidence and emit a non-mutating production promotion decision."
    )
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def _read_json(path: Path) -> tuple[dict, bool]:
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text) if text.strip() else {}
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (value, True) if isinstance(value, dict) and value else ({}, False)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    status, status_valid = _read_json(args.status)
    evaluation, evaluation_valid = _read_json(args.evaluation)
    audit, audit_valid = _read_json(args.audit)
    result = evaluate_production_promotion(status, evaluation, audit)

    if not status_valid and "human_labels_incomplete" not in result["failures"]:
        result["failures"].insert(0, "human_labels_incomplete")
        result["passed"] = False
    missing_inputs = []
    if not status_valid:
        missing_inputs.append("status")
    if not evaluation_valid:
        missing_inputs.append("evaluation")
    if not audit_valid:
        missing_inputs.append("audit")
    if missing_inputs:
        result["evidence"]["missing_or_blank_inputs"] = missing_inputs
        result["passed"] = False

    result["configuration_write_allowed"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
