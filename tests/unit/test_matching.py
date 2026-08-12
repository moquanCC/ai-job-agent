from src.matching.ranker import rank_jobs, score_job
from src.matching.score_fusion import fuse
from src.models.schemas import Education, Experience, JobProfile, ResumeProfile


def fixtures():
    resume = ResumeProfile(candidate_id="c", education=[Education(degree="硕士")], skills=["Python", "PyTorch", "大语言模型"], projects=[Experience(name="LLM", description="大模型问答", technologies=["Python", "大语言模型"], evidence=["使用 Python 开发大模型问答"])], raw_text="使用 Python 开发大模型问答")
    good = JobProfile(job_id="good", company="A", title="大模型算法工程师（校招）", location="上海", employment_type="校园招聘", required_skills=["Python", "大语言模型"], preferred_skills=["FAISS"], education_requirement="硕士及以上", raw_text="2027届校园招聘 大模型算法")
    weak = JobProfile(job_id="weak", company="B", title="数据挖掘工程师（校招）", location="上海", employment_type="校园招聘", required_skills=["SQL", "数据挖掘"], raw_text="2027届校园招聘 数据挖掘")
    return resume, good, weak


def test_fusion_arithmetic():
    values = {"required_skill": 100, "preferred_skill": 0, "project": 100, "semantic": 50, "education": 100, "location": 100}
    assert fuse(values) == 80


def test_scoring_explains_missing_skill_and_bounds():
    resume, good, _ = fixtures()
    result = score_job(resume, good)
    assert result.missing_preferred_skills == ["FAISS"]
    assert 0 <= result.total_score <= 100
    assert "Python" in result.matched_skills


def test_rank_order_is_stable_and_relevant_first():
    resume, good, weak = fixtures()
    results = rank_jobs(resume, [weak, good], top_k=2)
    assert [item.job_id for item in results] == ["good", "weak"]
