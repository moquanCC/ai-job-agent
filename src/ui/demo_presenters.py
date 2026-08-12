from __future__ import annotations

from urllib.parse import urlparse

from src.models.schemas import JobProfile


OFFICIAL_HOSTS = {
    "talent.baidu.com",
    "jobs.bilibili.com",
    "jobs.bytedance.com",
    "join.qq.com",
    "www.shlab.org.cn",
    "career.huawei.com",
    "campus.hr.xiaomi.com",
    "xiaomi.jobs.f.mioffice.cn",
    "zhaopin.meituan.com",
    "careers.aliyun.com",
}

STATUS_LABELS = {
    "active": "在招",
    "expired": "过期",
    "unknown": "待确认",
}


def source_badge(job: JobProfile) -> str:
    """Disclose source verification, job status, and verification date."""
    source_type = "官方公开页" if is_official_source(job) else "用户导入"
    checked_at = job.checked_at or job.last_checked_at
    checked_label = f"核验于 {checked_at}" if checked_at else "核验日期未知"
    return f"{source_type}｜{STATUS_LABELS[job.status]}｜{checked_label}"


def is_official_source(job: JobProfile) -> bool:
    """Return True only for an exact allowlisted official recruitment host."""
    return urlparse(job.source_url).hostname in OFFICIAL_HOSTS


def job_status_summary(jobs: list[JobProfile]) -> dict[str, int]:
    """Return stable, display-ready counts for the job library."""
    return {
        "全部": len(jobs),
        "在招": sum(job.status == "active" for job in jobs),
        "过期": sum(job.status == "expired" for job in jobs),
        "待确认": sum(job.status == "unknown" for job in jobs),
    }


def job_table_rows(jobs: list[JobProfile]) -> list[dict[str, str]]:
    """Convert job models into rows without coupling tests to Streamlit."""
    return [
        {
            "公司": job.company,
            "岗位": job.title,
            "地点": job.location,
            "状态": STATUS_LABELS[job.status],
            "核验日期": job.checked_at or job.last_checked_at,
            "官方来源": job.source_url,
        }
        for job in jobs
    ]


def ranking_comparison_rows(result: dict) -> list[dict]:
    """Convert ranking metrics into comparable rows and mark the best nDCG."""
    ranking = result["ranking"]
    best_ndcg = max(values["ndcg@10"] for values in ranking.values())
    return [
        {
            "方法": name,
            "Recall@5": values["recall@5"],
            "nDCG@10": values["ndcg@10"],
            "最佳 nDCG@10": values["ndcg@10"] == best_ndcg,
        }
        for name, values in ranking.items()
    ]
