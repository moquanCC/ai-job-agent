import json

from src.agents import JobAgentPreferences
from src.services import AnalysisService


def test_complete_offline_flow(tmp_path):
    service = AnalysisService(db_path=tmp_path / "app.db")
    jobs = [{"job_id": "j1", "company": "测试科技", "title": "大模型应用工程师（2027届校招）", "location": "上海", "employment_type": "校园招聘", "required_skills": ["Python", "大语言模型", "检索增强生成"], "preferred_skills": ["FAISS"], "description": "2027届校园招聘 大模型 RAG"}]
    count, errors = service.import_jobs("jobs.json", json.dumps(jobs, ensure_ascii=False).encode())
    assert count == 1 and not errors
    resume = service.parse_resume_file("resume.md", "硕士 计算机专业\n技能：Python、LLM、RAG\n项目经历\nRAG问答系统项目\n使用Python完成检索增强生成，召回提升10%。".encode())
    matches = service.rank(resume, 5)
    assert len(matches) == 1
    detail = service.build_detail(resume, matches[0].job_id, matches[0])
    assert "岗位匹配与简历优化报告" in detail["report"]
    assert detail["questions"]
    assert service.delete_candidate_data(resume.candidate_id) == 1


def test_job_decision_agent_flow_records_tools_and_backend(tmp_path):
    service = AnalysisService(db_path=tmp_path / "agent.db")
    jobs = [{"job_id": "j1", "company": "测试科技", "title": "RAG应用工程师（2027届校招）", "location": "上海", "employment_type": "校园招聘", "required_skills": ["Python", "检索增强生成"], "status": "active", "description": "2027届校园招聘 上海 RAG 检索增强生成"}]
    count, errors = service.import_jobs("jobs.json", json.dumps(jobs, ensure_ascii=False).encode())
    assert count == 1 and not errors
    resume = service.parse_resume_file(
        "resume.md",
        "硕士\n技能：Python、RAG\n项目经历\nRAG系统\n使用Python完成检索增强生成。".encode(),
    )

    result = service.run_job_agent(
        resume,
        JobAgentPreferences(location="上海", target_roles=["RAG"], explain_top_job=True),
    )

    assert result.status == "completed"
    assert [step.tool for step in result.trace] == [
        "search_jobs",
        "filter_eligibility",
        "rank_jobs",
        "explain_match",
    ]
    assert result.matches[0].job_id == "j1"
    assert result.actual_backend == service.embedder.name
