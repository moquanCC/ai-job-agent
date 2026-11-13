from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.models.schemas import JobProfile, MatchResult, ResumeProfile


JobToolName = Literal[
    "clarify_preferences",
    "search_jobs",
    "filter_eligibility",
    "rank_jobs",
    "explain_match",
]


class JobAgentPreferences(BaseModel):
    """User-controlled soft preferences and output options."""

    location: str = ""
    target_roles: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    explain_top_job: bool = False

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        return value.strip()

    @field_validator("target_roles")
    @classmethod
    def normalize_roles(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class JobToolCall(BaseModel):
    tool: JobToolName
    arguments: dict[str, Any] = Field(default_factory=dict)


class JobToolTrace(BaseModel):
    step: int = Field(ge=1)
    tool: JobToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["ok", "error"]
    result_count: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    backend: str = ""
    error: str = ""


class JobAgentResult(BaseModel):
    status: Literal["completed", "needs_clarification", "no_results", "error", "max_steps"]
    message: str
    matches: list[MatchResult] = Field(default_factory=list)
    explanation: str = ""
    clarification_questions: list[str] = Field(default_factory=list)
    trace: list[JobToolTrace] = Field(default_factory=list)
    stop_reason: str
    requested_backend: str
    actual_backend: str
    fallback_occurred: bool = False


@dataclass
class JobAgentState:
    resume: ResumeProfile
    preferences: JobAgentPreferences
    raw_jobs: list[JobProfile] | None = None
    eligible_jobs: list[JobProfile] | None = None
    matches: list[MatchResult] = field(default_factory=list)
    explanation: str = ""
    trace: list[JobToolTrace] = field(default_factory=list)
    seen_calls: set[str] = field(default_factory=set)

