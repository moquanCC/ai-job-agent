from src.matching.filters import filter_jobs
from src.models.schemas import JobProfile


def job(job_id, location="上海", text="2027届校园招聘 大模型算法", expired=False):
    return JobProfile(job_id=job_id, title="大模型算法工程师", location=location, raw_text=text, expired=expired, status="expired" if expired else "active")


def test_filter_requires_shanghai_campus_ai_and_active():
    jobs = [job("ok"), job("outside", "杭州"), job("social", text="社会招聘 大模型算法"), job("expired", expired=True)]
    assert [item.job_id for item in filter_jobs(jobs)] == ["ok"]


def test_filter_can_include_expired():
    assert len(filter_jobs([job("expired", expired=True)], include_expired=True)) == 1
