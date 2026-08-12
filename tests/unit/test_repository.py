from src.models.schemas import JobProfile
from src.repositories import AnalysisRepository, JobRepository


def test_job_upsert_deduplicates_by_company_title_url(tmp_path):
    repo = JobRepository(tmp_path / "test.db")
    first = JobProfile(job_id="a", company="公司", title="算法工程师", location="上海", source_url="u")
    second = JobProfile(job_id="b", company="公司", title="算法工程师", location="上海浦东", source_url="u")
    repo.upsert_many([first])
    repo.upsert_many([second])
    assert repo.count() == 1
    assert repo.list_jobs()[0].location == "上海浦东"


def test_analysis_delete_candidate(tmp_path):
    repo = AnalysisRepository(tmp_path / "test.db")
    repo.save("c1", "j1", {"score": 80})
    repo.save("c2", "j1", {"score": 70})
    assert repo.delete_candidate("c1") == 1
