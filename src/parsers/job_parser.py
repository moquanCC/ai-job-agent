from __future__ import annotations

import re
from datetime import date
from hashlib import sha1

from src.matching.skills import detect_skills, normalize_skills
from src.models.schemas import JobProfile


def _list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [part.strip(" -•") for part in re.split(r"[\n；;]", str(value)) if part.strip(" -•")]


def parse_job(record: dict) -> JobProfile:
    raw = str(record.get("raw_text") or record.get("description") or "")
    title = str(record.get("title") or "未命名岗位").strip()
    company = str(record.get("company") or "").strip()
    location = str(record.get("location") or ("上海" if "上海" in raw else "")).strip()
    all_skills = detect_skills(" ".join([title, raw]))
    required = normalize_skills(_list_value(record.get("required_skills"))) or all_skills
    preferred = normalize_skills(_list_value(record.get("preferred_skills")))
    deadline = str(record.get("deadline") or "")
    expired = bool(deadline and re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline) and deadline < date.today().isoformat())
    stable = "|".join([company, title, str(record.get("source_url") or "")])
    return JobProfile(
        job_id=str(record.get("job_id") or f"job_{sha1(stable.encode('utf-8')).hexdigest()[:10]}"),
        company=company,
        title=title,
        location=location,
        employment_type=str(record.get("employment_type") or ("校园招聘" if re.search(r"校招|应届|毕业生|2027届", raw) else "未知")),
        graduation_window=str(record.get("graduation_window") or ""),
        responsibilities=_list_value(record.get("responsibilities")) or _list_value(raw)[:12],
        required_skills=required,
        preferred_skills=preferred,
        education_requirement=str(record.get("education_requirement") or next((d + "及以上" for d in ("博士", "硕士", "本科", "大专") if d in raw), "")),
        major_requirements=_list_value(record.get("major_requirements")),
        keywords=normalize_skills(_list_value(record.get("keywords"))) or all_skills,
        source_url=str(record.get("source_url") or ""),
        published_at=str(record.get("published_at") or ""),
        deadline=deadline,
        raw_text=raw,
        expired=expired,
        status="expired" if expired else str(record.get("status") or "unknown"),
        last_checked_at=str(record.get("last_checked_at") or ""),
    )
