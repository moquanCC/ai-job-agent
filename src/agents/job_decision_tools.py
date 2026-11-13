from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.agents.resume_advisor import generate_advice
from src.matching.filters import filter_jobs
from src.matching.ranker import rank_jobs
from src.models.schemas import JobProfile, MatchResult, ResumeProfile
from src.retrieval.embeddings import TextEmbedder


class SearchJobsArgs(BaseModel):
    location: str = Field(min_length=1)
    target_roles: list[str] = Field(min_length=1)

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        return value.strip()

    @field_validator("target_roles")
    @classmethod
    def normalize_roles(cls, values: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not normalized:
            raise ValueError("target_roles 不能为空")
        return normalized


class FilterEligibilityArgs(BaseModel):
    job_ids: list[str] = Field(min_length=1)
    location: str = Field(min_length=1)


class RankJobsArgs(BaseModel):
    job_ids: list[str] = Field(min_length=1)
    location: str = Field(min_length=1)
    top_k: int = Field(ge=1, le=20)


class ExplainMatchArgs(BaseModel):
    job_id: str = Field(min_length=1)


class JobDecisionToolbox:
    """Validated deterministic tools exposed to the job-decision Agent."""

    def __init__(
        self,
        jobs: list[JobProfile],
        resume: ResumeProfile,
        embedder: TextEmbedder,
    ) -> None:
        self._jobs = {job.job_id: job for job in jobs}
        self.resume = resume
        self.embedder = embedder

    def search_jobs(self, args: SearchJobsArgs) -> list[JobProfile]:
        role_terms = tuple(term.casefold() for term in args.target_roles)
        result: list[JobProfile] = []
        for job in self._jobs.values():
            if args.location not in job.location:
                continue
            searchable = " ".join(
                [job.title, *job.responsibilities, *job.required_skills, job.raw_text]
            ).casefold()
            if any(term in searchable for term in role_terms):
                result.append(job)
        return sorted(result, key=lambda job: job.job_id)

    def filter_eligibility(self, args: FilterEligibilityArgs) -> list[JobProfile]:
        selected = [self._jobs[job_id] for job_id in args.job_ids if job_id in self._jobs]
        return filter_jobs(selected, location=args.location, include_expired=False)

    def rank_jobs(self, args: RankJobsArgs) -> list[MatchResult]:
        selected = [self._jobs[job_id] for job_id in args.job_ids if job_id in self._jobs]
        allowed = {job.job_id for job in selected}
        results = rank_jobs(
            self.resume,
            selected,
            top_k=args.top_k,
            location=args.location,
            include_expired=False,
            embedder=self.embedder,
        )
        if any(match.job_id not in allowed for match in results):
            raise ValueError("排序工具返回了候选白名单之外的岗位")
        return results

    def explain_match(self, args: ExplainMatchArgs, match: MatchResult) -> str:
        job = self._jobs.get(args.job_id)
        if job is None or match.job_id != args.job_id:
            raise ValueError("解释工具只能处理当前排名白名单内的岗位")
        advice = generate_advice(self.resume, job, match)
        evidence = "；".join(match.evidence) or "当前评分未产生额外证据"
        missing = "、".join(match.missing_required_skills) or "无"
        next_action = advice.items[0].suggestion if advice.items else "保留现有真实证据。"
        return (
            f"{job.company}｜{job.title}：总分 {match.total_score:.1f}/100。"
            f"评分依据：{evidence}。缺失必需技能：{missing}。下一步：{next_action}"
        )

