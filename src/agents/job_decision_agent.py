from __future__ import annotations

import json
from time import perf_counter

from src.agents.job_decision_models import (
    JobAgentPreferences,
    JobAgentResult,
    JobAgentState,
    JobToolCall,
    JobToolTrace,
)
from src.agents.job_decision_tools import (
    ExplainMatchArgs,
    FilterEligibilityArgs,
    JobDecisionToolbox,
    RankJobsArgs,
    SearchJobsArgs,
)
from src.models.schemas import JobProfile, ResumeProfile
from src.retrieval.embeddings import TextEmbedder


class JobDecisionAgent:
    """A bounded state machine that chooses and executes job-domain tools."""

    def __init__(
        self,
        jobs: list[JobProfile],
        embedder: TextEmbedder,
        *,
        requested_backend: str,
        max_steps: int = 6,
    ) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps 必须大于 0")
        self.jobs = jobs
        self.embedder = embedder
        self.requested_backend = requested_backend
        self.max_steps = max_steps

    def _backend_fields(self) -> dict[str, str | bool]:
        return {
            "requested_backend": self.requested_backend,
            "actual_backend": self.embedder.name,
            "fallback_occurred": bool(getattr(self.embedder, "fallback_occurred", False)),
        }

    @staticmethod
    def _missing_preferences(preferences: JobAgentPreferences) -> list[str]:
        missing: list[str] = []
        if not preferences.location:
            missing.append("location")
        if not preferences.target_roles:
            missing.append("target_roles")
        return missing

    def _next_call(self, state: JobAgentState) -> JobToolCall | None:
        missing = self._missing_preferences(state.preferences)
        if missing:
            return JobToolCall(tool="clarify_preferences", arguments={"missing_fields": missing})
        if state.raw_jobs is None:
            return JobToolCall(
                tool="search_jobs",
                arguments={
                    "location": state.preferences.location,
                    "target_roles": state.preferences.target_roles,
                },
            )
        if state.eligible_jobs is None:
            return JobToolCall(
                tool="filter_eligibility",
                arguments={
                    "job_ids": [job.job_id for job in state.raw_jobs],
                    "location": state.preferences.location,
                },
            )
        if not state.matches:
            return JobToolCall(
                tool="rank_jobs",
                arguments={
                    "job_ids": [job.job_id for job in state.eligible_jobs],
                    "location": state.preferences.location,
                    "top_k": state.preferences.top_k,
                },
            )
        if state.preferences.explain_top_job and not state.explanation:
            return JobToolCall(
                tool="explain_match",
                arguments={"job_id": state.matches[0].job_id},
            )
        return None

    @staticmethod
    def _questions(missing: list[str]) -> list[str]:
        labels = {
            "location": "你希望优先搜索哪个城市？",
            "target_roles": "你的目标岗位方向是什么（如 RAG、NLP、机器学习）？",
        }
        return [labels[field] for field in missing]

    def run(
        self,
        resume: ResumeProfile,
        preferences: JobAgentPreferences,
    ) -> JobAgentResult:
        state = JobAgentState(resume=resume, preferences=preferences)
        toolbox = JobDecisionToolbox(self.jobs, resume, self.embedder)

        for step in range(1, self.max_steps + 1):
            call = self._next_call(state)
            if call is None:
                return JobAgentResult(
                    status="completed",
                    message=f"已完成搜索、资格过滤和排序，返回 {len(state.matches)} 个岗位。",
                    matches=state.matches,
                    explanation=state.explanation,
                    trace=state.trace,
                    stop_reason="task_completed",
                    **self._backend_fields(),
                )

            signature = json.dumps(call.model_dump(), ensure_ascii=False, sort_keys=True)
            if signature in state.seen_calls:
                return JobAgentResult(
                    status="error",
                    message="检测到重复工具调用，已停止。",
                    trace=state.trace,
                    stop_reason="duplicate_tool_call",
                    **self._backend_fields(),
                )
            state.seen_calls.add(signature)
            started = perf_counter()
            try:
                count = self._execute(call, state, toolbox)
            except Exception as exc:
                state.trace.append(
                    JobToolTrace(
                        step=step,
                        tool=call.tool,
                        arguments=self._safe_arguments(call),
                        status="error",
                        latency_ms=(perf_counter() - started) * 1000,
                        backend=self.embedder.name,
                        error=str(exc),
                    )
                )
                return JobAgentResult(
                    status="error",
                    message=f"工具 {call.tool} 执行失败，已停止。",
                    trace=state.trace,
                    stop_reason="tool_error",
                    **self._backend_fields(),
                )
            state.trace.append(
                JobToolTrace(
                    step=step,
                    tool=call.tool,
                    arguments=self._safe_arguments(call),
                    status="ok",
                    result_count=count,
                    latency_ms=(perf_counter() - started) * 1000,
                    backend=self.embedder.name if call.tool == "rank_jobs" else "deterministic",
                )
            )
            if call.tool == "clarify_preferences":
                missing = self._missing_preferences(preferences)
                return JobAgentResult(
                    status="needs_clarification",
                    message="缺少关键求职条件，未擅自放宽硬约束。",
                    clarification_questions=self._questions(missing),
                    trace=state.trace,
                    stop_reason="missing_required_preferences",
                    **self._backend_fields(),
                )
            if call.tool == "search_jobs" and not state.raw_jobs:
                return JobAgentResult(
                    status="no_results",
                    message="当前岗位库没有符合城市和目标方向的岗位。",
                    trace=state.trace,
                    stop_reason="search_returned_no_jobs",
                    **self._backend_fields(),
                )
            if call.tool == "filter_eligibility" and not state.eligible_jobs:
                return JobAgentResult(
                    status="no_results",
                    message="搜索结果均未通过校招资格、地点和岗位状态过滤。",
                    trace=state.trace,
                    stop_reason="no_eligible_jobs",
                    **self._backend_fields(),
                )

        return JobAgentResult(
            status="max_steps",
            message="达到最大工具调用步数，已停止。",
            matches=state.matches,
            explanation=state.explanation,
            trace=state.trace,
            stop_reason="max_steps_reached",
            **self._backend_fields(),
        )

    @staticmethod
    def _safe_arguments(call: JobToolCall) -> dict:
        arguments = dict(call.arguments)
        if "job_ids" in arguments:
            arguments["job_count"] = len(arguments.pop("job_ids"))
        return arguments

    @staticmethod
    def _execute(
        call: JobToolCall,
        state: JobAgentState,
        toolbox: JobDecisionToolbox,
    ) -> int:
        if call.tool == "clarify_preferences":
            return len(call.arguments.get("missing_fields", []))
        if call.tool == "search_jobs":
            state.raw_jobs = toolbox.search_jobs(SearchJobsArgs.model_validate(call.arguments))
            return len(state.raw_jobs)
        if call.tool == "filter_eligibility":
            state.eligible_jobs = toolbox.filter_eligibility(
                FilterEligibilityArgs.model_validate(call.arguments)
            )
            return len(state.eligible_jobs)
        if call.tool == "rank_jobs":
            state.matches = toolbox.rank_jobs(RankJobsArgs.model_validate(call.arguments))
            return len(state.matches)
        if call.tool == "explain_match":
            args = ExplainMatchArgs.model_validate(call.arguments)
            match = next((item for item in state.matches if item.job_id == args.job_id), None)
            if match is None:
                raise ValueError("解释目标不在当前排名白名单中")
            state.explanation = toolbox.explain_match(args, match)
            return 1
        raise ValueError(f"未知工具：{call.tool}")

