from __future__ import annotations

from datetime import datetime

from src.models.schemas import AdviceReport, InterviewQuestion, JobProfile, MatchResult, ResumeProfile


def render_markdown_report(resume: ResumeProfile, job: JobProfile, match: MatchResult, advice: AdviceReport, questions: list[InterviewQuestion]) -> str:
    lines = [
        "# 岗位匹配与简历优化报告",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}｜候选人编号：`{resume.candidate_id}`",
        "",
        f"## {job.company}｜{job.title}",
        "",
        f"- 工作地点：{job.location}",
        f"- 总分：**{match.total_score:.1f}/100**",
        f"- 建议：{match.recommendation}",
        f"- 命中技能：{('、'.join(match.matched_skills) or '无')}",
        f"- 缺失硬技能：{('、'.join(match.missing_required_skills) or '无')}",
        "",
        "## 分项评分",
        "",
        "| 必需技能 | 加分技能 | 项目 | 语义 | 学历 | 地点 |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {match.subscores.required_skill:.1f} | {match.subscores.preferred_skill:.1f} | {match.subscores.project:.1f} | {match.subscores.semantic:.1f} | {match.subscores.education:.1f} | {match.subscores.location:.1f} |",
        "",
        "## 评分证据",
        "",
        *[f"- {item}" for item in (match.evidence or ["未找到额外证据"])],
        "",
        "## 简历建议",
        "",
    ]
    for item in advice.items:
        lines.extend([f"### {item.category}｜{item.action}", "", item.suggestion, "", f"> 依据：{item.evidence}", ""])
    lines.extend(["## 模拟面试", ""])
    for index, question in enumerate(questions, 1):
        lines.extend([f"### {index}. {question.question}", "", f"- 分类：{question.category}", f"- 考察点：{question.focus}", f"- 回答结构：{' → '.join(question.answer_structure)}", f"- 追问：{'；'.join(question.follow_ups)}", f"- 关联证据：{question.evidence}", ""])
    lines.extend(["---", "本报告基于用户提供的简历与岗位信息生成。缺失经历仅作为学习建议，不应直接写入简历。"])
    return "\n".join(lines)
