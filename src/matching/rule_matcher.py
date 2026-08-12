from __future__ import annotations

from src.models.schemas import JobProfile, ResumeProfile

DEGREE_LEVEL = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}


def skill_coverage(candidate: set[str], required: list[str]) -> tuple[float, list[str], list[str]]:
    if not required:
        return 100.0, [], []
    matched = [skill for skill in required if skill in candidate]
    missing = [skill for skill in required if skill not in candidate]
    return 100 * len(matched) / len(required), matched, missing


def education_score(resume: ResumeProfile, job: JobProfile) -> float:
    requirement = next((level for degree, level in DEGREE_LEVEL.items() if degree in job.education_requirement), 0)
    if requirement == 0:
        return 100.0
    candidate = max((DEGREE_LEVEL.get(item.degree, 0) for item in resume.education), default=0)
    return 100.0 if candidate >= requirement else 40.0


def project_overlap(resume: ResumeProfile, job: JobProfile) -> tuple[float, list[str]]:
    job_terms = set(job.required_skills + job.preferred_skills + job.keywords)
    project_terms = {skill for project in resume.projects + resume.research + resume.internships for skill in project.technologies}
    hits = sorted(job_terms & project_terms)
    return (100 * len(hits) / max(len(job_terms), 1), hits)
