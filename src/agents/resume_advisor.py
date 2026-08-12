from __future__ import annotations

from src.models.schemas import AdviceItem, AdviceReport, JobProfile, MatchResult, ResumeProfile


def generate_advice(resume: ResumeProfile, job: JobProfile, match: MatchResult) -> AdviceReport:
    highlights = [f"已命中 {skill}，可在相关项目中前置展示。" for skill in match.matched_skills[:5]]
    items: list[AdviceItem] = []

    for project in resume.projects[:3]:
        evidence = project.evidence[0] if project.evidence else project.description
        if evidence:
            tech = "、".join(project.technologies) or "现有技术"
            items.append(AdviceItem(
                category="项目描述",
                suggestion=f"将“{project.name}”按“问题—行动—结果”重排，并突出已使用的 {tech}；量化结果只保留原文已有数字。",
                evidence=evidence[:300],
                action="可直接修改",
            ))

    for skill in match.missing_required_skills:
        items.append(AdviceItem(
            category="技能缺口",
            suggestion=f"当前简历没有 {skill} 的可追溯证据。先完成学习或真实项目验证，再将其加入技能与项目描述。",
            evidence="原简历未检测到对应技能证据",
            action="完成相关工作后才能加入",
        ))

    for skill in match.missing_preferred_skills:
        items.append(AdviceItem(
            category="加分项缺口",
            suggestion=f"{skill} 是岗位加分项，但当前简历没有可追溯证据。可先完成一个最小实践并记录结果，通过验证后再加入。",
            evidence="原简历未检测到对应技能证据",
            action="完成相关工作后才能加入",
        ))

    if not items:
        items.append(AdviceItem(
            category="结构优化",
            suggestion="把与岗位职责最相关的真实项目移到项目经历首位，并保留原始事实与指标。",
            evidence=(resume.raw_text[:300] or "已确认的简历内容"),
            action="可直接修改",
        ))
    return AdviceReport(highlights=highlights, missing_required_skills=match.missing_required_skills, items=items)
