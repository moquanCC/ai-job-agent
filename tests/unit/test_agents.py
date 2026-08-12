from src.agents import generate_advice, generate_questions, render_markdown_report
from src.matching.ranker import score_job
from tests.unit.test_matching import fixtures


def test_advice_is_evidence_grounded_and_missing_skills_are_learning_only():
    resume, job, _ = fixtures()
    match = score_job(resume, job)
    advice = generate_advice(resume, job, match)
    assert all(item.evidence for item in advice.items)
    assert any(item.action == "完成相关工作后才能加入" for item in advice.items if "FAISS" in item.suggestion)


def test_questions_and_report_are_complete():
    resume, job, _ = fixtures()
    match = score_job(resume, job)
    advice = generate_advice(resume, job, match)
    questions = generate_questions(resume, job, match)
    report = render_markdown_report(resume, job, match, advice, questions)
    assert len(questions) >= 5
    assert all(q.focus and q.answer_structure and q.follow_ups and q.evidence for q in questions)
    assert "分项评分" in report and "缺失硬技能" in report
