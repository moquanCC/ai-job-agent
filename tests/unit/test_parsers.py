from src.matching.skills import detect_skills, normalize_skills
from src.parsers.file_parser import DocumentParseError, parse_document
from src.parsers.job_parser import parse_job
from src.parsers.resume_parser import parse_resume


def test_text_document_cleanup():
    parsed = parse_document("resume.md", "技能： Python  \n\n\n项目经历".encode())
    assert parsed.text == "技能： Python\n\n项目经历"


def test_skill_alias_normalization():
    assert normalize_skills(["torch", "RAG", "LLM"]) == ["PyTorch", "检索增强生成", "大语言模型"]
    assert "Python" in detect_skills("熟悉 Python3 与 PyTorch")


def test_resume_extracts_skills_education_and_project():
    text = "某大学 硕士 专业：计算机\n技能：Python、PyTorch、RAG\n项目经历\nRAG问答系统项目\n使用Python和FAISS，召回率提升12%。\n证书\nCET-6"
    profile = parse_resume(text, "candidate_test")
    assert profile.candidate_id == "candidate_test"
    assert {"Python", "PyTorch", "检索增强生成"} <= set(profile.skills)
    assert profile.education[0].degree == "硕士"
    assert profile.projects


def test_resume_stops_project_section_at_job_preference_heading():
    text = """## 项目经历
### 企业知识库 RAG 问答系统项目
使用 Python 和 FAISS 构建检索增强生成流程。

## 求职方向
大模型算法、AI 应用、数据挖掘
"""

    profile = parse_resume(text, "candidate_boundary")

    assert len(profile.projects) == 1
    assert profile.projects[0].name == "### 企业知识库 RAG 问答系统项目"
    assert "求职方向" not in profile.projects[0].description
    assert "数据挖掘" not in profile.projects[0].technologies
    assert "大模型算法" in profile.preferred_roles


def test_job_extracts_shanghai_and_expiry():
    job = parse_job({"job_id": "j1", "title": "大模型算法工程师", "description": "2027届校招，上海，要求 Python、LLM", "deadline": "2020-01-01"})
    assert job.location == "上海"
    assert job.expired is True
    assert "大语言模型" in job.required_skills


def test_unsupported_document_has_clear_error():
    try:
        parse_document("resume.exe", b"x")
    except DocumentParseError as exc:
        assert "不支持" in str(exc)
    else:
        raise AssertionError("expected parse error")
