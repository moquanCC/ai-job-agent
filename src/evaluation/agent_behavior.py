from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Sequence

from src.agents import JobAgentPreferences, JobDecisionAgent
from src.matching.ranker import rank_jobs
from src.models.schemas import JobProfile, ResumeProfile
from src.retrieval.embeddings import TextEmbedder


@dataclass(frozen=True)
class AgentScenario:
    scenario_id: str
    candidate_id: str
    location: str
    target_roles: tuple[str, ...]
    explain_top_job: bool
    expected_status: str
    expected_tools: tuple[str, ...]


def load_agent_scenarios(path: str | Path) -> list[AgentScenario]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        AgentScenario(
            scenario_id=row["id"],
            candidate_id=row["candidate_id"],
            location=row.get("location", ""),
            target_roles=tuple(row.get("target_roles", [])),
            explain_top_job=bool(row.get("explain_top_job", False)),
            expected_status=row["expected_status"],
            expected_tools=tuple(row["expected_tools"]),
        )
        for row in rows
    ]


def summarize_behavior_rows(rows: Sequence[dict]) -> dict[str, object]:
    if not rows:
        raise ValueError("Agent 行为评测不能为空")
    tool_calls = sum(len(row["actual_tools"]) for row in rows)
    expected_calls = sum(len(row["expected_tools"]) for row in rows)
    unnecessary_calls = sum(
        max(0, len(row["actual_tools"]) - len(row["expected_tools"])) for row in rows
    )
    return {
        "case_count": len(rows),
        "task_success_rate": fmean(float(row["task_success"]) for row in rows),
        "tool_selection_accuracy": fmean(
            float(row["tool_sequence_correct"]) for row in rows
        ),
        "tool_argument_validity": (
            sum(int(step_ok) for row in rows for step_ok in row["tool_steps_ok"]) / tool_calls
            if tool_calls
            else 0.0
        ),
        "average_tool_calls": tool_calls / len(rows),
        "unnecessary_call_rate": unnecessary_calls / max(tool_calls, expected_calls, 1),
        "stop_reasons": dict(sorted(Counter(row["stop_reason"] for row in rows).items())),
    }


def _fixed_workflow_case(
    scenario: AgentScenario,
    resume: ResumeProfile,
    jobs: list[JobProfile],
    embedder: TextEmbedder,
) -> dict:
    location = scenario.location or "上海"
    matches = rank_jobs(
        resume,
        jobs,
        top_k=5,
        location=location,
        include_expired=False,
        embedder=embedder,
    )
    can_complete_single_request = bool(
        scenario.location
        and scenario.target_roles
        and not scenario.explain_top_job
        and matches
    )
    return {
        "id": scenario.scenario_id,
        "status": "completed" if matches else "no_results",
        "task_success": can_complete_single_request,
        "actual_tools": ["filter_eligibility", "rank_jobs"],
        "expected_tools": list(scenario.expected_tools),
        "tool_sequence_correct": False,
        "tool_steps_ok": [True, True],
        "stop_reason": (
            "fixed_workflow_complete"
            if can_complete_single_request
            else "fixed_workflow_cannot_orchestrate_request"
        ),
    }


def evaluate_job_agent(
    scenarios: Sequence[AgentScenario],
    resumes: dict[str, ResumeProfile],
    jobs: list[JobProfile],
    embedder: TextEmbedder,
    *,
    requested_backend: str,
) -> dict[str, object]:
    if not scenarios:
        raise ValueError("Agent 行为评测不能为空")
    agent = JobDecisionAgent(
        jobs,
        embedder,
        requested_backend=requested_backend,
    )
    agent_rows: list[dict] = []
    fixed_rows: list[dict] = []
    for scenario in scenarios:
        resume = resumes[scenario.candidate_id]
        fixed_rows.append(_fixed_workflow_case(scenario, resume, jobs, embedder))
        result = agent.run(
            resume,
            JobAgentPreferences(
                location=scenario.location,
                target_roles=list(scenario.target_roles),
                top_k=5,
                explain_top_job=scenario.explain_top_job,
            ),
        )
        actual_tools = [step.tool for step in result.trace]
        agent_rows.append(
            {
                "id": scenario.scenario_id,
                "candidate_id": scenario.candidate_id,
                "status": result.status,
                "expected_status": scenario.expected_status,
                "task_success": result.status == scenario.expected_status,
                "actual_tools": actual_tools,
                "expected_tools": list(scenario.expected_tools),
                "tool_sequence_correct": actual_tools == list(scenario.expected_tools),
                "tool_steps_ok": [step.status == "ok" for step in result.trace],
                "stop_reason": result.stop_reason,
                "returned_job_ids": [match.job_id for match in result.matches],
                "actual_backend": result.actual_backend,
                "fallback_occurred": result.fallback_occurred,
            }
        )

    fixed_summary = summarize_behavior_rows(fixed_rows)
    agent_summary = summarize_behavior_rows(agent_rows)
    return {
        "dataset": {
            "synthetic": True,
            "human_gold": False,
            "purpose": "agent_behavior_and_tool_orchestration",
            "cases": len(scenarios),
        },
        "embedding": {
            "requested_backend": requested_backend,
            "actual_backend": embedder.name,
            "fallback_occurred": bool(getattr(embedder, "fallback_occurred", False)),
        },
        "fixed_workflow": {"summary": fixed_summary, "cases": fixed_rows},
        "agent": {"summary": agent_summary, "cases": agent_rows},
        "deltas": {
            "task_success_rate": agent_summary["task_success_rate"]
            - fixed_summary["task_success_rate"],
            "average_tool_calls": agent_summary["average_tool_calls"]
            - fixed_summary["average_tool_calls"],
        },
        "limitations": [
            "All scenarios and candidate profiles are synthetic; this benchmark is not human gold.",
            "Task success validates tool orchestration, not real recruitment or ranking quality.",
            "The planner is a bounded deterministic policy, not an open-ended autonomous agent.",
        ],
    }

