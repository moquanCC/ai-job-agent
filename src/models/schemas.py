from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    field: str
    text: str


class Education(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: str = ""
    end_date: str = ""


class Experience(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"candidate_{uuid4().hex[:8]}")
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[Experience] = Field(default_factory=list)
    research: list[Experience] = Field(default_factory=list)
    internships: list[Experience] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=lambda: ["上海"])
    preferred_roles: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    raw_text: str = ""

    @field_validator("skills", "certificates", "preferred_locations", "preferred_roles")
    @classmethod
    def unique_values(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(v.strip() for v in values if v and v.strip()))


class JobProfile(BaseModel):
    job_id: str
    company: str = ""
    title: str
    location: str = ""
    employment_type: str = "校园招聘"
    graduation_window: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education_requirement: str = ""
    major_requirements: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source_url: str = ""
    published_at: str = ""
    deadline: str = ""
    raw_text: str = ""
    expired: bool = False
    status: Literal["active", "expired", "unknown"] = "unknown"
    last_checked_at: str = ""

    @field_validator("required_skills", "preferred_skills", "keywords")
    @classmethod
    def unique_skills(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(v.strip() for v in values if v and v.strip()))


class Subscores(BaseModel):
    required_skill: float = Field(ge=0, le=100)
    preferred_skill: float = Field(ge=0, le=100)
    project: float = Field(ge=0, le=100)
    semantic: float = Field(ge=0, le=100)
    education: float = Field(ge=0, le=100)
    location: float = Field(ge=0, le=100)


class MatchResult(BaseModel):
    candidate_id: str
    job_id: str
    total_score: float = Field(ge=0, le=100)
    subscores: Subscores
    matched_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommendation: str


class AdviceItem(BaseModel):
    category: str
    suggestion: str
    evidence: str = ""
    action: Literal["可直接修改", "完成相关工作后才能加入"]


class AdviceReport(BaseModel):
    highlights: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    items: list[AdviceItem] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    category: str
    question: str
    focus: str
    answer_structure: list[str]
    follow_ups: list[str]
    evidence: str
    difficulty: Literal["基础", "进阶", "挑战"] = "进阶"


class ParsedDocument(BaseModel):
    filename: str
    text: str
    paragraphs: list[str]
    metadata: dict[str, str] = Field(default_factory=dict)
