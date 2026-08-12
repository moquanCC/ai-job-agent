from __future__ import annotations

import numpy as np

from src.matching.ranker import rank_jobs, score_job
from src.matching.semantic_matcher import semantic_scores
from src.models.schemas import Education, JobProfile, ResumeProfile


class CountingEmbedder:
    name = "counting"

    def __init__(self) -> None:
        self.batches: list[int] = []

    def encode(self, texts: list[str]) -> np.ndarray:
        self.batches.append(len(texts))
        return np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1))


def _resume() -> ResumeProfile:
    return ResumeProfile(
        candidate_id="candidate",
        education=[Education(degree="硕士")],
        skills=["Python", "大语言模型"],
        preferred_roles=["算法工程师"],
        raw_text="Python 大语言模型项目",
    )


def _job(job_id: str, *, location: str = "上海", expired: bool = False) -> JobProfile:
    return JobProfile(
        job_id=job_id,
        company="测试公司",
        title="大模型算法工程师（校招）",
        location=location,
        employment_type="校园招聘",
        required_skills=["Python"],
        raw_text="2027届校园招聘 大模型算法",
        expired=expired,
        status="expired" if expired else "active",
    )


def test_semantic_scores_encodes_query_and_documents_as_two_batches() -> None:
    embedder = CountingEmbedder()

    scores = semantic_scores("candidate", ["job one", "job two"], embedder)

    assert scores == [100.0, 100.0]
    assert embedder.batches == [1, 2]


def test_semantic_scores_skips_encoding_when_there_are_no_documents() -> None:
    embedder = CountingEmbedder()

    assert semantic_scores("candidate", [], embedder) == []
    assert embedder.batches == []


def test_rank_jobs_encodes_one_query_and_one_eligible_job_batch() -> None:
    embedder = CountingEmbedder()
    jobs = [
        _job("eligible-1"),
        _job("wrong-location", location="北京"),
        _job("expired", expired=True),
        _job("eligible-2"),
    ]

    results = rank_jobs(_resume(), jobs, embedder=embedder)

    assert embedder.batches == [1, 2]
    assert {result.job_id for result in results} == {"eligible-1", "eligible-2"}


def test_score_job_uses_precomputed_semantic_score() -> None:
    result = score_job(_resume(), _job("job"), semantic_score=37.5)

    assert result.subscores.semantic == 37.5
