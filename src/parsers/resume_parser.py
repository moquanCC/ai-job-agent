from __future__ import annotations

import re

from src.matching.skills import detect_skills
from src.models.schemas import Education, Evidence, Experience, ResumeProfile

DEGREES = ("博士", "硕士", "本科", "大专")
PROJECT_MARKERS = ("项目经历", "项目经验", "科研经历")


def _section(text: str, markers: tuple[str, ...]) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if any(m in line for m in markers)), None)
    if start is None:
        return ""
    end_markers = ("教育经历", "技能清单", "专业技能", "实习经历", "证书", "个人信息", "获奖经历", "科研经历")
    end = next((i for i in range(start + 1, len(lines)) if any(m == lines[i].strip() or lines[i].strip().startswith(m + "：") for m in end_markers)), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def parse_resume(text: str, candidate_id: str | None = None) -> ResumeProfile:
    skills = detect_skills(text)
    evidence = [Evidence(field="skills", text=line[:300]) for line in text.splitlines() if detect_skills(line)][:12]

    education: list[Education] = []
    for line in text.splitlines():
        degree = next((degree for degree in DEGREES if degree in line), "")
        if degree:
            major_match = re.search(r"(?:专业|方向)[:：]?\s*([^|，,；;\n]+)", line)
            school_match = re.search(r"([\u4e00-\u9fa5A-Za-z]+(?:大学|学院))", line)
            education.append(Education(school=school_match.group(1) if school_match else "", degree=degree, major=major_match.group(1).strip() if major_match else ""))

    project_text = _section(text, PROJECT_MARKERS)
    projects: list[Experience] = []
    if project_text:
        blocks = [b.strip() for b in re.split(r"\n(?=[^\n]{2,40}(?:项目|系统|平台|模型|Agent))", project_text) if b.strip()]
        for block in blocks[:6]:
            lines = block.splitlines()
            metrics = re.findall(r"[^。；;\n]*(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?倍|降低|提升)[^。；;\n]*", block)
            projects.append(Experience(name=lines[0][:80], description=" ".join(lines[1:])[:1000], technologies=detect_skills(block), responsibilities=lines[1:8], metrics=[m.strip() for m in metrics], evidence=[block[:500]]))

    certificates = [line.strip(" -•") for line in text.splitlines() if re.search(r"证书|CET[- ]?[46]|N[1-5]|雅思|托福", line, re.I)][:10]
    roles = [role for role in ("大模型算法", "AI应用", "数据挖掘", "推荐系统", "数据科学") if role in text]
    payload = dict(
        education=education,
        skills=skills,
        projects=projects,
        certificates=certificates,
        preferred_locations=["上海"] if "上海" in text or not re.search(r"北京|深圳|广州|杭州", text) else [],
        preferred_roles=roles,
        evidence=evidence,
        raw_text=text,
    )
    if candidate_id:
        payload["candidate_id"] = candidate_id
    return ResumeProfile(**payload)
