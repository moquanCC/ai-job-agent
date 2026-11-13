from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from src.agents import (
    JobAgentPreferences,
    JobDecisionAgent,
    generate_advice,
    generate_questions,
    render_markdown_report,
)
from src.config import Settings, database_path
from src.matching.ranker import rank_jobs
from src.models.schemas import JobProfile, ResumeProfile
from src.parsers import parse_document, parse_job, parse_resume
from src.repositories import AnalysisRepository, JobRepository
from src.retrieval import TextEmbedder, create_embedder


ROOT = Path(__file__).resolve().parents[2]


class AnalysisService:
    def __init__(
        self,
        settings: Settings | None = None,
        db_path: str | Path | None = None,
        embedder: TextEmbedder | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.embedder = embedder or create_embedder(
            self.settings.embedding_backend,
            model_name=self.settings.embedding_model,
            device=self.settings.embedding_device or None,
            batch_size=self.settings.embedding_batch_size,
            max_length=self.settings.embedding_max_length,
        )
        path = Path(db_path) if db_path else database_path(self.settings.database_url)
        self.jobs = JobRepository(path)
        self.analyses = AnalysisRepository(path)

    @property
    def embedding_status(self) -> dict[str, str | bool]:
        """Return auditable requested/selected backend state without loading a model."""
        actual = self.embedder.name
        return {
            "requested_backend": self.settings.embedding_backend,
            "actual_backend": actual,
            "model": actual,
            "fallback_occurred": bool(getattr(self.embedder, "fallback_occurred", False)),
        }

    def parse_resume_file(self, filename: str, content: bytes) -> ResumeProfile:
        document = parse_document(filename, content)
        return parse_resume(document.text)

    def import_jobs(self, filename: str, content: bytes) -> tuple[int, list[str]]:
        errors: list[str] = []
        suffix = Path(filename).suffix.lower()
        try:
            if suffix == ".json":
                records = json.loads(content.decode("utf-8-sig"))
                records = records if isinstance(records, list) else records.get("jobs", [])
            elif suffix == ".csv":
                records = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            else:
                raise ValueError("岗位批量导入仅支持 CSV 或 JSON")
        except Exception as exc:
            return 0, [str(exc)]
        parsed: list[JobProfile] = []
        for index, record in enumerate(records, 1):
            try:
                parsed.append(parse_job(record))
            except Exception as exc:
                errors.append(f"第 {index} 条：{exc}")
        return self.jobs.upsert_many(parsed), errors

    def import_verified_jobs(self, dataset_path: str | Path | None = None) -> tuple[int, dict[str, int]]:
        path = Path(dataset_path) if dataset_path is not None else ROOT / "data" / "real_jobs" / "jobs.json"
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("官方岗位数据必须是 JSON 列表")

        jobs = [JobProfile.model_validate(record) for record in records]
        statuses = {
            status: sum(job.status == status for job in jobs)
            for status in ("active", "expired", "unknown")
        }
        return self.jobs.upsert_many(jobs), statuses

    def load_real_evaluation(self, result_path: str | Path | None = None) -> dict:
        path = Path(result_path) if result_path is not None else ROOT / "data" / "real_jobs" / "evaluation_results.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict) or result.get("dataset", {}).get("human_gold") is not False:
            raise ValueError("评测披露字段缺失或不合法")
        return result

    def add_pasted_job(self, text: str, title: str = "粘贴岗位", company: str = "用户导入") -> JobProfile:
        job = parse_job({"company": company, "title": title, "location": "上海" if "上海" in text else "", "description": text})
        self.jobs.upsert_many([job])
        return job

    def rank(self, resume: ResumeProfile, top_k: int | None = None, include_expired: bool = False):
        return rank_jobs(
            resume,
            self.jobs.list_jobs(),
            top_k=top_k or self.settings.top_k,
            location=self.settings.default_location,
            include_expired=include_expired,
            embedder=self.embedder,
        )

    def run_job_agent(
        self,
        resume: ResumeProfile,
        preferences: JobAgentPreferences,
    ):
        agent = JobDecisionAgent(
            self.jobs.list_jobs(),
            self.embedder,
            requested_backend=self.settings.embedding_backend,
        )
        return agent.run(resume, preferences)

    def build_detail(self, resume: ResumeProfile, job_id: str, match, difficulty: str = "进阶") -> dict:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError("岗位不存在或已被删除")
        advice = generate_advice(resume, job, match)
        questions = generate_questions(resume, job, match, difficulty)
        report = render_markdown_report(resume, job, match, advice, questions)
        self.analyses.save(resume.candidate_id, job_id, {"match": match.model_dump(), "advice": advice.model_dump()})
        return {"job": job, "advice": advice, "questions": questions, "report": report}

    def delete_candidate_data(self, candidate_id: str) -> int:
        return self.analyses.delete_candidate(candidate_id)
