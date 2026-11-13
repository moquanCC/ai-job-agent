from __future__ import annotations

import re

from src.models.schemas import JobProfile, ResumeProfile

DEGREE_LEVEL = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}

_SKILL_ALIASES = {
    "llm": "llm",
    "largelanguagemodel": "llm",
    "大语言模型": "llm",
    "大模型": "llm",
    "sklearn": "sklearn",
    "scikitlearn": "sklearn",
    "nlp": "nlp",
    "自然语言处理": "nlp",
    "rag": "rag",
    "检索增强生成": "rag",
}


def normalize_skill(value: str) -> str:
    """Return a deterministic comparison key without changing display labels."""

    compact = re.sub(r"[\s._/+-]+", "", value.casefold())
    return _SKILL_ALIASES.get(compact, compact)


def skill_coverage(candidate: set[str], required: list[str]) -> tuple[float, list[str], list[str]]:
    if not required:
        return 100.0, [], []
    candidate_keys = {normalize_skill(skill) for skill in candidate}
    matched = [skill for skill in required if normalize_skill(skill) in candidate_keys]
    missing = [skill for skill in required if normalize_skill(skill) not in candidate_keys]
    return 100 * len(matched) / len(required), matched, missing


def education_score(resume: ResumeProfile, job: JobProfile) -> float:
    requirement = next((level for degree, level in DEGREE_LEVEL.items() if degree in job.education_requirement), 0)
    if requirement == 0:
        return 100.0
    candidate = max((DEGREE_LEVEL.get(item.degree, 0) for item in resume.education), default=0)
    return 100.0 if candidate >= requirement else 40.0


def project_overlap(resume: ResumeProfile, job: JobProfile) -> tuple[float, list[str]]:
    job_terms = list(dict.fromkeys(job.required_skills + job.preferred_skills + job.keywords))
    project_terms = {
        normalize_skill(skill)
        for project in resume.projects + resume.research + resume.internships
        for skill in project.technologies
    }
    hits = sorted(term for term in job_terms if normalize_skill(term) in project_terms)
    return (100 * len(hits) / max(len(job_terms), 1), hits)
