from __future__ import annotations

from src.matching.filters import filter_jobs
from src.matching.rule_matcher import education_score, project_overlap, skill_coverage
from src.matching.score_fusion import fuse, recommendation
from src.matching.semantic_matcher import semantic_similarity
from src.models.schemas import JobProfile, MatchResult, ResumeProfile, Subscores


def _resume_text(resume: ResumeProfile) -> str:
    projects = " ".join(p.description + " " + " ".join(p.technologies) for p in resume.projects)
    return " ".join(resume.skills + resume.preferred_roles) + " " + projects


def _job_text(job: JobProfile) -> str:
    return " ".join([job.title, *job.responsibilities, *job.required_skills, *job.preferred_skills, job.raw_text])


def score_job(resume: ResumeProfile, job: JobProfile, custom_weights: dict[str, float] | None = None) -> MatchResult:
    candidate = set(resume.skills)
    required, matched_required, missing_required = skill_coverage(candidate, job.required_skills)
    preferred, matched_preferred, missing_preferred = skill_coverage(candidate, job.preferred_skills)
    project, project_hits = project_overlap(resume, job)
    semantic = semantic_similarity(_resume_text(resume), _job_text(job))
    values = {
        "required_skill": required,
        "preferred_skill": preferred,
        "project": project,
        "semantic": semantic,
        "education": education_score(resume, job),
        "location": 100.0 if "上海" in job.location else 0.0,
    }
    total = fuse(values, custom_weights)
    evidence = []
    if matched_required:
        evidence.append("硬技能命中：" + "、".join(matched_required))
    if project_hits:
        evidence.append("项目技术命中：" + "、".join(project_hits))
    if resume.evidence:
        evidence.append("简历依据：" + resume.evidence[0].text[:160])
    return MatchResult(
        candidate_id=resume.candidate_id,
        job_id=job.job_id,
        total_score=total,
        subscores=Subscores(**{key: round(value, 2) for key, value in values.items()}),
        matched_skills=sorted(set(matched_required + matched_preferred + project_hits)),
        missing_required_skills=missing_required,
        missing_preferred_skills=missing_preferred,
        evidence=evidence,
        recommendation=recommendation(total),
    )


def rank_jobs(resume: ResumeProfile, jobs: list[JobProfile], top_k: int = 10, location: str = "上海", include_expired: bool = False, custom_weights: dict[str, float] | None = None) -> list[MatchResult]:
    eligible = filter_jobs(jobs, location=location, include_expired=include_expired)
    results = [score_job(resume, job, custom_weights) for job in eligible]
    return sorted(results, key=lambda item: (-item.total_score, item.job_id))[:top_k]
