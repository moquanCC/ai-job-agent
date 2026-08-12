from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "research" / "official-shanghai-ai-jobs.md"
OUT = ROOT / "data" / "real_jobs"

FIELD_NAMES = {
    "company",
    "title",
    "location",
    "employment_type/graduation wording",
    "responsibilities",
    "required_skills",
    "preferred_skills",
    "education_requirement",
    "source_url",
    "published_at/deadline",
    "status",
    "quoted_evidence",
    "checked_at",
}


def split_items(value: str) -> list[str]:
    if value in {"", "未单列"}:
        return []
    return [item.strip() for item in re.split(r"[；;]", value) if item.strip()]


def parse_source() -> list[dict]:
    text = SOURCE.read_text(encoding="utf-8")
    sections = re.findall(r"^### (\d+)\. (.+?)\n(.*?)(?=^### \d+\.|^## 数据概览)", text, re.M | re.S)
    jobs: list[dict] = []
    for number, heading, body in sections:
        fields: dict[str, str] = {}
        for line in body.splitlines():
            match = re.match(r"^- ([^:]+):\s*(.*)$", line)
            if match and match.group(1) in FIELD_NAMES:
                fields[match.group(1)] = match.group(2).strip()

        published_deadline = fields["published_at/deadline"].split("；", 1)
        published_at = published_deadline[0].strip()
        deadline_text = published_deadline[1].strip() if len(published_deadline) == 2 else ""
        deadline_match = re.search(r"\d{4}-\d{2}-\d{2}", deadline_text)
        graduation = fields["employment_type/graduation wording"]
        graduation_match = re.search(r"\d{4}-\d{2}-\d{2}\s*至\s*\d{4}-\d{2}-\d{2}", graduation)
        source_evidence = re.findall(r"“([^”]+)”", fields["quoted_evidence"])
        responsibilities = split_items(fields["responsibilities"])
        required = split_items(fields["required_skills"])
        preferred = split_items(fields["preferred_skills"])
        raw_text = "；".join(responsibilities + required + preferred)
        title = fields.get("title") or heading.split("｜", 1)[-1]

        jobs.append(
            {
                "job_id": f"real_baidu_{int(number):03d}",
                "company": fields["company"],
                "title": title,
                "location": fields["location"],
                "employment_type": "校园招聘",
                "graduation_window": graduation_match.group(0) if graduation_match else graduation,
                "responsibilities": responsibilities,
                "required_skills": required,
                "preferred_skills": preferred,
                "education_requirement": fields["education_requirement"],
                "keywords": list(dict.fromkeys(required + preferred)),
                "source_url": fields["source_url"],
                "published_at": published_at,
                "deadline": deadline_match.group(0) if deadline_match else "",
                "status": fields["status"],
                "checked_at": fields["checked_at"],
                "source_evidence": source_evidence or [fields["quoted_evidence"]],
                "raw_text": raw_text,
            }
        )
    return jobs


def build_labels(jobs: list[dict]) -> list[dict]:
    profiles = {
        "eval_llm": ("LLM/RAG 工程画像", {"多模态": 2, "infra": 2, "agent": 2, "强化学习": 2, "视觉语言": 2, "测试": 2, "搜广推": 1, "计算机视觉": 1, "异构": 1, "决策规划": 1}),
        "eval_mining": ("数据挖掘/推荐画像", {"搜广推": 3, "计算机视觉": 1, "多模态": 1, "测试": 1, "决策规划": 1}),
        "eval_nlp": ("NLP/深度学习画像", {"多模态": 2, "agent": 2, "视觉语言": 2, "计算机视觉": 1, "infra": 1, "强化学习": 1, "搜广推": 1, "测试": 1, "异构": 1}),
    }
    labels: list[dict] = []
    for candidate_id, (profile_name, rules) in profiles.items():
        for job in jobs:
            haystack = f"{job['title']} {' '.join(job['responsibilities'])}".lower()
            matched = [(term, grade) for term, grade in rules.items() if term.lower() in haystack]
            grade = max((grade for _, grade in matched), default=0)
            terms = "、".join(term for term, value in matched if value == grade)
            reason = f"{profile_name}与岗位的{terms}方向{'高度' if grade == 3 else '部分' if grade == 2 else '弱' if grade == 1 else '不'}匹配。" if matched else f"{profile_name}与该岗位核心方向缺少直接交集。"
            labels.append(
                {
                    "candidate_id": candidate_id,
                    "job_id": job["job_id"],
                    "grade": grade,
                    "annotator": "codex-rule-assisted-v1",
                    "rationale": reason,
                    "labeled_at": "2026-08-12",
                }
            )
    return labels


def validate(jobs: list[dict], labels: list[dict]) -> None:
    assert len(jobs) == 15
    assert len({job["job_id"] for job in jobs}) == len(jobs)
    assert len({job["source_url"] for job in jobs}) == len(jobs)
    assert all(job["source_url"].startswith("https://talent.baidu.com/jobs/detail/") for job in jobs)
    assert all("上海" in job["location"] for job in jobs)
    assert all(job["checked_at"] and job["source_evidence"] for job in jobs)
    assert {job["status"] for job in jobs} <= {"active", "expired", "unknown"}
    assert len(labels) == 3 * len(jobs)
    assert all(0 <= label["grade"] <= 3 for label in labels)


def main() -> None:
    jobs = parse_source()
    labels = build_labels(jobs)
    validate(jobs, labels)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "relevance_labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"compiled {len(jobs)} jobs and {len(labels)} relevance labels")


if __name__ == "__main__":
    main()
