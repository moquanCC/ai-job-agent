from __future__ import annotations

from src.models.schemas import JobProfile

ROLE_TERMS = (
    "AI",
    "人工智能",
    "算法",
    "大模型",
    "机器学习",
    "数据挖掘",
    "数据科学",
    "推荐",
    "搜索",
    "NLP",
    "自然语言",
    "RAG",
    "检索增强生成",
)
CAMPUS_TERMS = ("校园招聘", "校招", "应届", "毕业生", "2027")


def filter_jobs(jobs: list[JobProfile], location: str = "上海", include_expired: bool = False) -> list[JobProfile]:
    result: list[JobProfile] = []
    for job in jobs:
        searchable = " ".join([job.title, job.raw_text, job.employment_type])
        if location and location not in job.location:
            continue
        if not any(term.casefold() in searchable.casefold() for term in ROLE_TERMS):
            continue
        if any(term in searchable for term in ("社会招聘", "社招")):
            continue
        if not any(term.casefold() in searchable.casefold() for term in CAMPUS_TERMS):
            continue
        if not include_expired and (job.expired or job.status == "expired"):
            continue
        result.append(job)
    return result
