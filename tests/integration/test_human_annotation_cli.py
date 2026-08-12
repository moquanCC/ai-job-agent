from __future__ import annotations

import json

from scripts import build_human_gold, import_human_annotations
from src.evaluation.human_gold import prepare_task_spec


def test_import_cli_emits_false_readiness_for_template(tmp_path):
    tasks = {"task_fingerprint": "t", "pair_fingerprint": "p", "pairs": [{"candidate_id": "c", "job_id": "j"}]}
    annotation = {"metadata": {"status": "template_not_completed", "template": True}, "rows": []}
    tasks_path, input_path, output_path = tmp_path / "tasks.json", tmp_path / "input.json", tmp_path / "out.json"
    tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
    input_path.write_text(json.dumps(annotation), encoding="utf-8")

    code = import_human_annotations.main(["--tasks", str(tasks_path), "--input", str(input_path), "--role", "A", "--output", str(output_path)])

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert code == 1
    assert result["human_gold"] is False
    assert result["status"] == "human_labels_incomplete"
    assert result["failures"]


def test_build_cli_emits_false_readiness_when_inputs_missing(tmp_path):
    output = tmp_path / "gold.json"
    code = build_human_gold.main([
        "--tasks", str(tmp_path / "tasks.json"), "--annotator-a", str(tmp_path / "a.json"),
        "--annotator-b", str(tmp_path / "b.json"), "--adjudication", str(tmp_path / "c.json"),
        "--output", str(output),
    ])
    result = json.loads(output.read_text(encoding="utf-8"))
    assert code == 1
    assert result["human_gold"] is False
    assert result["status"] == "human_labels_incomplete"


def test_repository_bare_750_tasks_and_manifest_are_supported(tmp_path):
    tasks_path = import_human_annotations.Path("data/human_gold/annotation_tasks.json")
    manifest_path = import_human_annotations.Path("data/human_gold/split_manifest.json")
    raw = json.loads(tasks_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = prepare_task_spec(raw, manifest)
    assert len(spec["pairs"]) == 750
    assert spec["task_fingerprint"] == manifest["sha256_fingerprint"]
    assert len(spec["pair_fingerprint"]) == 64

    template = {"metadata": {"status": "template_not_completed", "template": True}, "rows": []}
    template_path, output = tmp_path / "template.json", tmp_path / "status.json"
    template_path.write_text(json.dumps(template), encoding="utf-8")
    code = import_human_annotations.main(["--tasks", str(tasks_path), "--manifest", str(manifest_path), "--input", str(template_path), "--role", "A", "--output", str(output)])
    status = json.loads(output.read_text(encoding="utf-8"))
    assert code == 1
    assert status["human_gold"] is False


def test_import_csv_bridge_accepts_bom_and_injects_metadata(tmp_path):
    tasks = {"task_fingerprint": "t", "pair_fingerprint": "p", "pairs": [{"candidate_id": "c", "job_id": "j"}]}
    tasks_path, csv_path, output = tmp_path / "tasks.json", tmp_path / "answers.csv", tmp_path / "validated.json"
    tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
    csv_path.write_text("Task ID,Candidate ID,Job ID,候选方向,候选证据,公司｜岗位,岗位职责与要求,Grade 0-3,Rationale（必填）,Confidence\nt,c,j,NLP,项目证据,公司岗位,要求,2,匹配证据充分,high\n", encoding="utf-8-sig")
    code = import_human_annotations.main([
        "--tasks", str(tasks_path), "--input", str(csv_path), "--role", "A",
        "--annotator-id", "human-a", "--completed-at", "2026-08-13T10:00:00+08:00",
        "--output", str(output),
    ])
    result = json.loads(output.read_text(encoding="utf-8"))
    assert code == 0
    assert result["metadata"]["annotator_id"] == "human-a"
    assert result["rows"][0]["grade"] == 2


def test_import_csv_rejects_wrong_headers_and_partial_real_coverage(tmp_path):
    tasks = "data/human_gold/annotation_tasks.json"; manifest = "data/human_gold/split_manifest.json"
    csv_path, output = tmp_path / "partial.csv", tmp_path / "status.json"
    csv_path.write_text("Candidate ID,Job ID,Grade,Rationale（必填）,Confidence\nx,y,2,理由,high\n", encoding="utf-8-sig")
    code = import_human_annotations.main([
        "--tasks", tasks, "--manifest", manifest, "--input", str(csv_path), "--role", "A",
        "--annotator-id", "human-a", "--completed-at", "2026-08-13", "--output", str(output),
    ])
    assert code == 1
    assert "列头" in json.loads(output.read_text(encoding="utf-8"))["failures"][0]

    csv_path.write_text("Candidate ID,Job ID,Grade 0-3,Rationale（必填）,Confidence\nsynthetic_01_llm_rag,real_baidu_001,2,理由,high\n", encoding="utf-8-sig")
    code = import_human_annotations.main([
        "--tasks", tasks, "--manifest", manifest, "--input", str(csv_path), "--role", "A",
        "--annotator-id", "human-a", "--completed-at", "2026-08-13", "--output", str(output),
    ])
    assert code == 1
    assert "覆盖" in json.loads(output.read_text(encoding="utf-8"))["failures"][0]


def test_build_gold_accepts_adjudication_csv_bridge(tmp_path):
    tasks = {"task_fingerprint": "t", "pair_fingerprint": "p", "pairs": [{"candidate_id": "c", "job_id": "j"}]}
    tasks_path = tmp_path / "tasks.json"; tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
    def annotation(role, who, grade):
        return {"metadata": {"annotator_id": who, "role": role, "completed_at": "2026-08-13", "task_fingerprint": "t", "pair_fingerprint": "p", "status": "completed", "template": False}, "rows": [{"candidate_id": "c", "job_id": "j", "grade": grade, "rationale": "独立证据"}]}
    a_path, b_path = tmp_path / "a.json", tmp_path / "b.json"
    a_path.write_text(json.dumps(annotation("A", "human-a", 3)), encoding="utf-8")
    b_path.write_text(json.dumps(annotation("B", "human-b", 1)), encoding="utf-8")
    adjudication, output = tmp_path / "adjudication.csv", tmp_path / "gold.json"
    adjudication.write_text("Task ID,Candidate ID,Job ID,候选方向,候选证据,公司｜岗位,岗位职责与要求,A Grade（导入后）,B Grade（导入后）,分歧状态,Final Grade,裁决理由,Confidence\nt,c,j,NLP,证据,公司岗位,要求,3,1,分歧,2,第三人核对证据,high\n", encoding="utf-8-sig")
    code = build_human_gold.main(["--tasks", str(tasks_path), "--annotator-a", str(a_path), "--annotator-b", str(b_path), "--adjudication", str(adjudication), "--adjudicator-id", "human-c", "--completed-at", "2026-08-14", "--output", str(output)])
    result = json.loads(output.read_text(encoding="utf-8"))
    assert code == 0
    assert result["human_gold"] is True
    assert result["rows"][0]["grade"] == 2


def test_csv_bridge_rejects_duplicate_or_empty_headers(tmp_path):
    tasks = {"task_fingerprint": "t", "pair_fingerprint": "p", "pairs": [{"candidate_id": "c", "job_id": "j"}]}
    tasks_path = tmp_path / "tasks.json"; tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
    output = tmp_path / "status.json"
    for header in (
        "Candidate ID,Job ID,Grade 0-3,Rationale（必填）,Confidence,Confidence",
        "Candidate ID,Job ID,Grade 0-3,Rationale（必填）,Confidence,",
    ):
        csv_path = tmp_path / "bad.csv"; csv_path.write_text(header + "\nc,j,2,理由,high,x\n", encoding="utf-8-sig")
        code = import_human_annotations.main(["--tasks", str(tasks_path), "--input", str(csv_path), "--role", "A", "--annotator-id", "human-a", "--completed-at", "2026-08-13", "--output", str(output)])
        assert code == 1
        assert "列头" in json.loads(output.read_text(encoding="utf-8"))["failures"][0]
