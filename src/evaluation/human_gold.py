from __future__ import annotations

import hashlib
import json
import csv
import io

from sklearn.metrics import cohen_kappa_score


def _pairs(tasks: dict) -> list[tuple[str, str]]:
    rows = tasks.get("pairs") or tasks.get("tasks")
    if not isinstance(rows, list) or not rows:
        raise ValueError("任务缺少 pairs")
    pairs = [(str(r["candidate_id"]), str(r["job_id"])) for r in rows]
    if len(pairs) != len(set(pairs)):
        raise ValueError("任务存在重复 pair")
    return pairs


def prepare_task_spec(tasks_payload: dict | list, manifest: dict | None = None) -> dict:
    """Normalize the repository's bare task list into a fingerprinted task spec."""
    if isinstance(tasks_payload, dict):
        return tasks_payload
    if not isinstance(tasks_payload, list):
        raise ValueError("tasks 必须是裸列表或标准 task spec")
    if not isinstance(manifest, dict) or not manifest.get("sha256_fingerprint"):
        raise ValueError("裸 tasks 列表必须配套冻结 manifest")
    canonical = [
        {
            "task_id": str(row.get("task_id", "")),
            "candidate_id": str(row["candidate_id"]),
            "job_id": str(row["job_id"]),
        }
        for row in tasks_payload
    ]
    canonical.sort(key=lambda row: (row["task_id"], row["candidate_id"], row["job_id"]))
    pair_fingerprint = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "task_fingerprint": str(manifest["sha256_fingerprint"]),
        "split_fingerprint": str(manifest["sha256_fingerprint"]),
        "pair_fingerprint": pair_fingerprint,
        "candidate_splits": manifest.get("candidate_splits"),
        "counts": manifest.get("counts"),
        "pairs": tasks_payload,
    }


def annotation_document_from_csv(text: str, *, annotator_id: str, role: str, completed_at: str, tasks: dict) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    required = ["Candidate ID", "Job ID", "Grade 0-3", "Rationale（必填）", "Confidence"]
    _require_csv_headers(reader.fieldnames, required, "CSV")
    rows = []
    for row in reader:
        raw_grade = row["Grade 0-3"].strip()
        grade = int(raw_grade) if raw_grade and raw_grade.lstrip("-").isdigit() else None
        rows.append({"candidate_id": row["Candidate ID"].strip(), "job_id": row["Job ID"].strip(), "grade": grade, "rationale": row["Rationale（必填）"].strip(), "confidence": row["Confidence"].strip()})
    return {"metadata": {"annotator_id": annotator_id, "role": role, "completed_at": completed_at, "task_fingerprint": tasks["task_fingerprint"], "pair_fingerprint": tasks["pair_fingerprint"], "status": "completed", "template": False}, "rows": rows}


def adjudication_document_from_csv(text: str, *, annotator_id: str, completed_at: str, tasks: dict) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    required = ["Candidate ID", "Job ID", "Final Grade", "裁决理由"]
    _require_csv_headers(reader.fieldnames, required, "裁决 CSV")
    rows = []
    for row in reader:
        raw_grade = row["Final Grade"].strip()
        grade = int(raw_grade) if raw_grade and raw_grade.lstrip("-").isdigit() else None
        rows.append({"candidate_id": row["Candidate ID"].strip(), "job_id": row["Job ID"].strip(), "grade": grade, "rationale": row["裁决理由"].strip()})
    return {"metadata": {"annotator_id": annotator_id, "role": "adjudicator", "completed_at": completed_at, "task_fingerprint": tasks["task_fingerprint"], "pair_fingerprint": tasks["pair_fingerprint"], "status": "completed", "template": False}, "rows": rows}


def _require_csv_headers(fieldnames: list[str] | None, required: list[str], label: str) -> None:
    if not fieldnames or any(not isinstance(name, str) or not name.strip() for name in fieldnames):
        raise ValueError(f"{label} 列头不能为空")
    if len(fieldnames) != len(set(fieldnames)):
        raise ValueError(f"{label} 列头不能重复")
    missing = [name for name in required if name not in fieldnames]
    if missing:
        raise ValueError(f"{label} 列头必须包含：{', '.join(required)}；缺少：{', '.join(missing)}")


def validate_annotation(document: dict, tasks: dict, expected_role: str) -> dict:
    meta = document.get("metadata", {})
    if meta.get("template") is True or meta.get("status") != "completed":
        raise ValueError("模板或未完成文件不是人类标注")
    for key in ("annotator_id", "role", "completed_at", "task_fingerprint", "pair_fingerprint"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"metadata.{key} 不能为空")
    if meta["role"] != expected_role:
        raise ValueError(f"role 必须为 {expected_role}")
    if (meta["task_fingerprint"], meta["pair_fingerprint"]) != (tasks.get("task_fingerprint"), tasks.get("pair_fingerprint")):
        raise ValueError("fingerprint 与冻结任务不匹配")
    expected, normalized, seen = _pairs(tasks), {}, set()
    for row in document.get("rows", []):
        pair = (str(row.get("candidate_id", "")), str(row.get("job_id", "")))
        if pair in seen:
            raise ValueError("存在重复 pair")
        seen.add(pair)
        grade, rationale = row.get("grade"), row.get("rationale")
        if not isinstance(grade, int) or isinstance(grade, bool):
            raise ValueError("grade 必须是 0-3 整数")
        if grade not in range(4):
            raise ValueError("grade 必须在 0-3 范围")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("rationale 不能为空")
        normalized[pair] = {"candidate_id": pair[0], "job_id": pair[1], "grade": grade, "rationale": rationale.strip()}
    if seen != set(expected):
        raise ValueError(f"覆盖不一致：期望 {len(expected)}，实际 {len(seen)}")
    return {"metadata": dict(meta), "rows": [normalized[p] for p in expected]}


def compute_human_agreement(a: dict, b: dict) -> dict:
    if a["metadata"]["role"] != "A" or b["metadata"]["role"] != "B":
        raise ValueError("agreement 需要完整 A/B 标注")
    if a["metadata"]["annotator_id"] == b["metadata"]["annotator_id"]:
        raise ValueError("A/B 标注者身份不得相同")
    left = {(r["candidate_id"], r["job_id"]): r["grade"] for r in a["rows"]}
    right = {(r["candidate_id"], r["job_id"]): r["grade"] for r in b["rows"]}
    if left.keys() != right.keys():
        raise ValueError("A/B 覆盖不一致")
    order = sorted(left); x, y = [left[p] for p in order], [right[p] for p in order]
    return {"count": len(order), "exact_agreement": sum(i == j for i, j in zip(x, y, strict=True)) / len(order), "quadratic_weighted_kappa": float(cohen_kappa_score(x, y, labels=[0, 1, 2, 3], weights="quadratic")), "disagreement_count": sum(i != j for i, j in zip(x, y, strict=True))}


def build_human_gold(a: dict, b: dict, adjudication: dict, tasks: dict) -> dict:
    agreement = compute_human_agreement(a, b); meta = adjudication.get("metadata", {})
    identities = {a["metadata"]["annotator_id"], b["metadata"]["annotator_id"]}
    if meta.get("annotator_id") in identities:
        raise ValueError("裁决者必须是身份不同的第三人")
    if meta.get("role") != "adjudicator" or meta.get("status") != "completed" or meta.get("template") is True:
        raise ValueError("裁决必须由第三人完整完成")
    for key in ("annotator_id", "completed_at", "task_fingerprint", "pair_fingerprint"):
        if not isinstance(meta.get(key), str) or not meta[key].strip(): raise ValueError(f"裁决 metadata.{key} 不能为空")
    if (meta["task_fingerprint"], meta["pair_fingerprint"]) != (tasks.get("task_fingerprint"), tasks.get("pair_fingerprint")): raise ValueError("裁决 fingerprint 不匹配")
    ar = {(r["candidate_id"], r["job_id"]): r for r in a["rows"]}; br = {(r["candidate_id"], r["job_id"]): r for r in b["rows"]}
    disagreements = {p for p in ar if ar[p]["grade"] != br[p]["grade"]}; decisions = {}
    for row in adjudication.get("rows", []):
        pair = (str(row.get("candidate_id", "")), str(row.get("job_id", ""))); grade, rationale = row.get("grade"), row.get("rationale")
        if pair in decisions: raise ValueError("裁决存在重复 pair")
        if pair not in disagreements: raise ValueError("裁决只能包含分歧 pair")
        if not isinstance(grade, int) or isinstance(grade, bool) or grade not in range(4): raise ValueError("裁决 grade 必须是 0-3 整数")
        if not isinstance(rationale, str) or not rationale.strip(): raise ValueError("裁决 rationale 不能为空")
        decisions[pair] = {"grade": grade, "rationale": rationale.strip()}
    if set(decisions) != disagreements: raise ValueError("每个分歧必须由第三人提供 grade 与 rationale")
    rows = []
    for pair in _pairs(tasks):
        final, decision = (decisions[pair], "adjudicated") if pair in disagreements else ({"grade": ar[pair]["grade"], "rationale": "A/B 独立标注一致"}, "agreement")
        rows.append({"candidate_id": pair[0], "job_id": pair[1], **final, "decision": decision})
    splits = tasks.get("candidate_splits") or {}
    candidate_ids = {row["candidate_id"] for row in rows}
    return {"human_gold": True, "status": "complete", "candidate_count": len(candidate_ids), "pair_count": len(rows), "task_fingerprint": tasks["task_fingerprint"], "pair_fingerprint": tasks["pair_fingerprint"], "split": {"fingerprint": tasks.get("split_fingerprint", tasks["task_fingerprint"]), "train_candidates": list(splits.get("train", [])), "validation_candidates": list(splits.get("validation", [])), "blind_test_candidates": list(splits.get("blind_test", []))}, "annotators": {"A": a["metadata"]["annotator_id"], "B": b["metadata"]["annotator_id"], "adjudicator": meta["annotator_id"]}, "agreement": agreement, "rows": rows}


def readiness_failure(*failures: str) -> dict:
    return {"human_gold": False, "status": "human_labels_incomplete", "failures": list(filter(None, failures))}
