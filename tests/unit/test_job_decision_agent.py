from __future__ import annotations

from src.agents import JobAgentPreferences, JobDecisionAgent
from src.models.schemas import Evidence, JobProfile, ResumeProfile
from src.retrieval.embeddings import HashingEmbedder


def fixtures() -> tuple[ResumeProfile, list[JobProfile]]:
    resume = ResumeProfile(
        candidate_id="candidate_agent",
        skills=["Python", "检索增强生成", "FAISS"],
        preferred_roles=["RAG"],
        evidence=[Evidence(field="skills", text="使用 Python 和 FAISS 实现 RAG。")],
        raw_text="合成候选人，不含联系方式。",
    )
    jobs = [
        JobProfile(
            job_id="active-rag",
            company="测试科技",
            title="RAG 应用工程师（2027届校招）",
            location="上海",
            employment_type="校园招聘",
            required_skills=["Python", "检索增强生成"],
            preferred_skills=["FAISS"],
            status="active",
            raw_text="2027届校园招聘，上海 RAG 应用工程师。",
        ),
        JobProfile(
            job_id="expired-rag",
            company="过期科技",
            title="RAG 算法工程师（2027届校招）",
            location="上海",
            employment_type="校园招聘",
            status="expired",
            expired=True,
            raw_text="2027届校园招聘，上海 RAG 算法工程师。",
        ),
        JobProfile(
            job_id="beijing-rag",
            company="异地科技",
            title="RAG 工程师（2027届校招）",
            location="北京",
            employment_type="校园招聘",
            status="active",
            raw_text="2027届校园招聘，北京 RAG 工程师。",
        ),
    ]
    return resume, jobs


def make_agent(*, max_steps: int = 6) -> JobDecisionAgent:
    _, jobs = fixtures()
    return JobDecisionAgent(
        jobs,
        HashingEmbedder(),
        requested_backend="hashing",
        max_steps=max_steps,
    )


def test_agent_executes_search_filter_and_rank_with_auditable_trace() -> None:
    resume, _ = fixtures()
    result = make_agent().run(
        resume,
        JobAgentPreferences(location="上海", target_roles=["RAG"], top_k=5),
    )

    assert result.status == "completed"
    assert [step.tool for step in result.trace] == [
        "search_jobs",
        "filter_eligibility",
        "rank_jobs",
    ]
    assert [match.job_id for match in result.matches] == ["active-rag"]
    assert result.actual_backend == "local-hashing-v1"
    assert result.fallback_occurred is False
    assert all("resume" not in step.arguments for step in result.trace)


def test_rag_role_is_treated_as_an_ai_eligible_job() -> None:
    resume, _ = fixtures()
    result = make_agent().run(
        resume,
        JobAgentPreferences(location="上海", target_roles=["RAG"]),
    )

    assert result.status == "completed"
    assert result.matches[0].job_id == "active-rag"


def test_agent_clarifies_missing_preferences_without_searching() -> None:
    resume, _ = fixtures()
    result = make_agent().run(resume, JobAgentPreferences())

    assert result.status == "needs_clarification"
    assert [step.tool for step in result.trace] == ["clarify_preferences"]
    assert len(result.clarification_questions) == 2
    assert result.stop_reason == "missing_required_preferences"


def test_agent_optionally_calls_grounded_explanation_tool() -> None:
    resume, _ = fixtures()
    result = make_agent().run(
        resume,
        JobAgentPreferences(
            location="上海",
            target_roles=["RAG"],
            explain_top_job=True,
        ),
    )

    assert result.status == "completed"
    assert [step.tool for step in result.trace][-1] == "explain_match"
    assert "测试科技" in result.explanation
    assert "评分依据" in result.explanation


def test_agent_stops_at_configured_maximum_steps() -> None:
    resume, _ = fixtures()
    result = make_agent(max_steps=2).run(
        resume,
        JobAgentPreferences(location="上海", target_roles=["RAG"]),
    )

    assert result.status == "max_steps"
    assert len(result.trace) == 2
    assert result.stop_reason == "max_steps_reached"
