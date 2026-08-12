from __future__ import annotations

import copy

import pytest

from src.evaluation.human_gold import (
    build_human_gold,
    compute_human_agreement,
    prepare_task_spec,
    validate_annotation,
)


def _tasks():
    rows = [{"candidate_id": "c1", "job_id": "j1"}, {"candidate_id": "c1", "job_id": "j2"}]
    return {"task_fingerprint": "task-sha", "pair_fingerprint": "pair-sha", "pairs": rows}


def _annotation(role: str, annotator: str, grades=(2, 1)):
    return {
        "metadata": {
            "annotator_id": annotator,
            "role": role,
            "completed_at": "2026-08-12T12:00:00+08:00",
            "task_fingerprint": "task-sha",
            "pair_fingerprint": "pair-sha",
            "status": "completed",
            "template": False,
        },
        "rows": [
            {"candidate_id": "c1", "job_id": "j1", "grade": grades[0], "rationale": "证据一"},
            {"candidate_id": "c1", "job_id": "j2", "grade": grades[1], "rationale": "证据二"},
        ],
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda doc: doc["rows"][0].update(grade=None), "grade"),
        (lambda doc: doc["rows"][0].update(grade=4), "0-3"),
        (lambda doc: doc["rows"][0].update(grade=True), "整数"),
        (lambda doc: doc["rows"][0].update(rationale=""), "rationale"),
        (lambda doc: doc["rows"].append(copy.deepcopy(doc["rows"][0])), "重复"),
        (lambda doc: doc["rows"].pop(), "覆盖"),
        (lambda doc: doc["metadata"].update(task_fingerprint="wrong"), "fingerprint"),
        (lambda doc: doc["metadata"].update(status="template_not_completed", template=True), "模板"),
    ],
)
def test_validate_annotation_rejects_incomplete_or_invalid_rows(mutation, message):
    doc = _annotation("A", "human-a")
    mutation(doc)
    with pytest.raises(ValueError, match=message):
        validate_annotation(doc, _tasks(), expected_role="A")


def test_agreement_requires_complete_distinct_a_and_b():
    a = validate_annotation(_annotation("A", "same"), _tasks(), expected_role="A")
    b = validate_annotation(_annotation("B", "same"), _tasks(), expected_role="B")
    with pytest.raises(ValueError, match="身份不得相同"):
        compute_human_agreement(a, b)


def test_build_gold_requires_distinct_third_party_for_every_disagreement():
    a = validate_annotation(_annotation("A", "human-a", (3, 1)), _tasks(), expected_role="A")
    b = validate_annotation(_annotation("B", "human-b", (1, 1)), _tasks(), expected_role="B")
    adjudication = {
        "metadata": {
            "annotator_id": "human-a",
            "role": "adjudicator",
            "completed_at": "2026-08-13T12:00:00+08:00",
            "task_fingerprint": "task-sha",
            "pair_fingerprint": "pair-sha",
            "status": "completed",
            "template": False,
        },
        "rows": [{"candidate_id": "c1", "job_id": "j1", "grade": 2, "rationale": "裁决证据"}],
    }
    with pytest.raises(ValueError, match="第三人"):
        build_human_gold(a, b, adjudication, _tasks())


def test_build_gold_sets_true_only_after_complete_adjudication():
    a = validate_annotation(_annotation("A", "human-a", (3, 1)), _tasks(), expected_role="A")
    b = validate_annotation(_annotation("B", "human-b", (1, 1)), _tasks(), expected_role="B")
    adjudication = {
        "metadata": {
            "annotator_id": "human-c",
            "role": "adjudicator",
            "completed_at": "2026-08-13T12:00:00+08:00",
            "task_fingerprint": "task-sha",
            "pair_fingerprint": "pair-sha",
            "status": "completed",
            "template": False,
        },
        "rows": [{"candidate_id": "c1", "job_id": "j1", "grade": 2, "rationale": "裁决证据"}],
    }
    result = build_human_gold(a, b, adjudication, _tasks())
    assert result["human_gold"] is True
    assert len(result["rows"]) == 2
    assert result["rows"][0]["decision"] == "adjudicated"
    assert result["rows"][1]["decision"] == "agreement"


def test_task_spec_and_complete_gold_carry_promotion_gate_metadata():
    raw = [
        {"task_id": "t1", "candidate_id": "c1", "job_id": "j1"},
        {"task_id": "t2", "candidate_id": "c1", "job_id": "j2"},
    ]
    manifest = {
        "sha256_fingerprint": "frozen-sha",
        "candidate_splits": {"train": ["c1"], "validation": [], "blind_test": []},
        "counts": {"candidates": 1, "train": 1, "validation": 0, "blind_test": 0, "pairs": 2},
    }
    tasks = prepare_task_spec(raw, manifest)
    assert tasks["candidate_splits"] == manifest["candidate_splits"]
    assert tasks["counts"] == manifest["counts"]
    assert tasks["split_fingerprint"] == "frozen-sha"

    a_doc = _annotation("A", "human-a")
    b_doc = _annotation("B", "human-b")
    for document in (a_doc, b_doc):
        document["metadata"]["task_fingerprint"] = tasks["task_fingerprint"]
        document["metadata"]["pair_fingerprint"] = tasks["pair_fingerprint"]
    a = validate_annotation(a_doc, tasks, "A")
    b = validate_annotation(b_doc, tasks, "B")
    adjudication = {
        "metadata": {
            "annotator_id": "human-c", "role": "adjudicator",
            "completed_at": "2026-08-13", "task_fingerprint": tasks["task_fingerprint"],
            "pair_fingerprint": tasks["pair_fingerprint"], "status": "completed", "template": False,
        },
        "rows": [],
    }
    result = build_human_gold(a, b, adjudication, tasks)
    assert result["candidate_count"] == 1
    assert result["pair_count"] == 2
    assert result["split"] == {
        "fingerprint": "frozen-sha",
        "train_candidates": ["c1"],
        "validation_candidates": [],
        "blind_test_candidates": [],
    }
    assert set(result["agreement"]) >= {"exact_agreement", "quadratic_weighted_kappa"}
