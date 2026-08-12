from src.models.schemas import JobProfile
from src.ui.demo_presenters import (
    job_status_summary,
    job_table_rows,
    is_official_source,
    ranking_comparison_rows,
    source_badge,
)


def test_ranking_comparison_rows_marks_best_ndcg():
    result = {
        "ranking": {
            "keyword": {"recall@5": 0.15, "ndcg@10": 0.61},
            "rule_fusion": {"recall@5": 0.49, "ndcg@10": 0.73},
        }
    }

    rows = ranking_comparison_rows(result)

    assert rows[1]["最佳 nDCG@10"] is True
    assert rows[0]["最佳 nDCG@10"] is False


def test_job_status_summary_and_source_rows():
    jobs = [
        JobProfile(
            job_id="j",
            company="测试公司",
            title="算法工程师",
            location="上海",
            status="active",
            source_url="https://example.com/jobs/j",
            checked_at="2026-08-12",
        )
    ]

    assert job_status_summary(jobs) == {
        "全部": 1,
        "在招": 1,
        "过期": 0,
        "待确认": 0,
    }
    assert job_table_rows(jobs)[0] == {
        "公司": "测试公司",
        "岗位": "算法工程师",
        "地点": "上海",
        "状态": "在招",
        "核验日期": "2026-08-12",
        "官方来源": "https://example.com/jobs/j",
    }


def test_job_status_summary_covers_all_statuses_and_checked_at_fallback():
    jobs = [
        JobProfile(job_id="active", title="A", status="active"),
        JobProfile(
            job_id="expired",
            title="B",
            status="expired",
            last_checked_at="2026-08-11",
        ),
        JobProfile(job_id="unknown", title="C", status="unknown"),
    ]

    assert job_status_summary(jobs) == {
        "全部": 3,
        "在招": 1,
        "过期": 1,
        "待确认": 1,
    }
    assert job_table_rows(jobs)[1]["状态"] == "过期"
    assert job_table_rows(jobs)[1]["核验日期"] == "2026-08-11"


def test_source_badge_discloses_verified_official_source():
    job = JobProfile(
        job_id="j",
        company="测试公司",
        title="算法工程师",
        status="active",
        source_url="https://talent.baidu.com/jobs/detail/j",
        checked_at="2026-08-12",
    )

    assert source_badge(job) == "官方公开页｜在招｜核验于 2026-08-12"


def test_source_badge_treats_unverified_url_as_user_import():
    job = JobProfile(
        job_id="j",
        title="算法工程师",
        status="expired",
        source_url="https://example.com/jobs/j",
    )

    assert source_badge(job) == "用户导入｜过期｜核验日期未知"


def test_source_badge_requires_exact_official_hostname():
    lookalike = JobProfile(
        job_id="lookalike",
        title="算法工程师",
        status="unknown",
        source_url="https://talent.baidu.com.example.com/jobs/j",
        last_checked_at="2026-08-11",
    )
    official_with_port = JobProfile(
        job_id="official",
        title="算法工程师",
        status="unknown",
        source_url="https://JOBS.BILIBILI.COM:443/campus/positions/1",
        last_checked_at="2026-08-11",
    )

    assert source_badge(lookalike) == "用户导入｜待确认｜核验于 2026-08-11"
    assert source_badge(official_with_port) == "官方公开页｜待确认｜核验于 2026-08-11"
    assert is_official_source(lookalike) is False
    assert is_official_source(official_with_port) is True
