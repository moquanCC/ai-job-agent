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


def embedding_status_rows(status: dict, requested_model: str) -> dict[str, str]:
    """Format runtime embedding state without causing first model encoding."""
    requested = str(status.get("requested_backend", "unknown"))
    actual = str(status.get("actual_backend", "unknown"))
    fallback = bool(status.get("fallback_occurred", False))
    if requested == "auto" and actual == "auto":
        return {
            "请求后端": requested,
            "实际后端": "尚未首次编码",
            "模型": f"{requested_model}（候选，尚未加载）",
            "回退": "否",
        }
    actual_backend = "hashing" if actual == "local-hashing-v1" else actual
    return {
        "请求后端": requested,
        "实际后端": actual_backend,
        "模型": str(status.get("model", actual)),
        "回退": "是" if fallback else "否",
    }


def embedding_benchmark_rows(hashing_result: dict, bge_result: dict) -> list[dict]:
    """Return measured backend metrics and signed deltas, without winner claims."""
    embedding = bge_result.get("parameters", {}).get("embedding", {})
    if embedding.get("actual_backend") != "bge-m3":
        raise ValueError("BGE-M3 评测文件未声明实际后端为 bge-m3")
    hashing_metrics = hashing_result["ranking"]["full"]
    bge_metrics = bge_result["ranking"]["full"]
    return [
        {
            "指标": label,
            "hashing": hashing_metrics[key],
            "BGE-M3": bge_metrics[key],
            "实测差值": round(bge_metrics[key] - hashing_metrics[key], 4),
        }
        for key, label in (("recall@5", "Recall@5"), ("mrr", "MRR"), ("ndcg@10", "nDCG@10"))
    ]


def fusion_tuning_rows(result: dict) -> list[dict]:
    """Expose fixed, descriptive and held-out metrics as distinct scopes."""
    entries = (
        ("固定基线", result["baseline"]["metrics"]),
        ("描述性（调参后）", result["deployment_candidate"]["metrics"]),
        ("留一候选人验证", result["loco"]["mean_metrics"]),
    )
    return [
        {
            "评估口径": scope,
            "Recall@5": metrics["recall@5"],
            "nDCG@5": metrics["ndcg@5"],
            "nDCG@10": metrics["ndcg@10"],
        }
        for scope, metrics in entries
    ]


def fusion_tuning_summary(result: dict) -> dict:
    """Summarize fold uncertainty and a non-promotional guardrail decision."""
    failure_labels = {
        "exploratory_insufficient_candidates": "样本仅含 3 个合成候选人",
        "human_gold_false": "human_gold=false",
        "descriptive_ndcg5_gain_below_0_005": "描述性 nDCG@5 提升不足 0.005",
        "descriptive_recall5_below_baseline": "描述性 Recall@5 低于基线",
        "descriptive_recall10_drop_over_0_02": "描述性 Recall@10 降幅超过 0.02",
        "loco_mean_ndcg5_below_baseline": "LOCO 平均 nDCG@5 低于基线",
    }
    fold_values = [fold["held_out_metrics"]["ndcg@5"] for fold in result["loco"]["folds"]]
    stable = result["search"]["fold_winner_stability"]["stable_across_all_folds"]
    return {
        "promotion": "未拒绝" if result["guardrails"]["passed"] else "拒绝",
        "failure_reasons": [
            failure_labels.get(reason, reason) for reason in result["guardrails"].get("failures", [])
        ],
        "fold_ndcg5_range": [min(fold_values), max(fold_values)],
        "unique_fold_winners": result["loco"]["winner_diagnostics"]["unique_winner_count"],
        "stable_across_all_folds": bool(stable),
    }
