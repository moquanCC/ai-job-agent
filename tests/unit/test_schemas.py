import pytest
from pydantic import ValidationError

from src.models.schemas import JobProfile, MatchResult, ResumeProfile, Subscores


def test_resume_skills_are_unique():
    resume = ResumeProfile(skills=["Python", "Python", " SQL "])
    assert resume.skills == ["Python", "SQL"]


def test_job_requires_identifier_and_title():
    with pytest.raises(ValidationError):
        JobProfile.model_validate({"title": "算法工程师"})


def test_match_score_is_bounded():
    with pytest.raises(ValidationError):
        MatchResult(candidate_id="c", job_id="j", total_score=101, subscores=Subscores(required_skill=0, preferred_skill=0, project=0, semantic=0, education=0, location=0), recommendation="x")
