from __future__ import annotations

import pytest

from src.evaluation.agent_behavior import summarize_behavior_rows


def test_behavior_summary_uses_hand_calculated_rates() -> None:
    rows = [
        {
            "task_success": True,
            "tool_sequence_correct": True,
            "actual_tools": ["search_jobs", "rank_jobs"],
            "expected_tools": ["search_jobs", "rank_jobs"],
            "tool_steps_ok": [True, True],
            "stop_reason": "task_completed",
        },
        {
            "task_success": False,
            "tool_sequence_correct": False,
            "actual_tools": ["search_jobs", "search_jobs"],
            "expected_tools": ["clarify_preferences"],
            "tool_steps_ok": [True, False],
            "stop_reason": "tool_error",
        },
    ]

    summary = summarize_behavior_rows(rows)

    assert summary["task_success_rate"] == 0.5
    assert summary["tool_selection_accuracy"] == 0.5
    assert summary["tool_argument_validity"] == 0.75
    assert summary["average_tool_calls"] == 2.0
    assert summary["unnecessary_call_rate"] == pytest.approx(0.25)


def test_behavior_summary_rejects_empty_dataset() -> None:
    with pytest.raises(ValueError, match="不能为空"):
        summarize_behavior_rows([])

