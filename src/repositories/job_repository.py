from __future__ import annotations

import json
from pathlib import Path

from src.models.schemas import JobProfile
from src.repositories.database import connect, initialize


class JobRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        with connect(self.path) as connection:
            initialize(connection)

    def upsert_many(self, jobs: list[JobProfile]) -> int:
        with connect(self.path) as connection:
            initialize(connection)
            for job in jobs:
                connection.execute(
                    """INSERT INTO jobs(job_id, company, title, location, source_url, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(company, title, source_url) DO UPDATE SET
                      job_id=excluded.job_id, location=excluded.location,
                      payload=excluded.payload, updated_at=CURRENT_TIMESTAMP""",
                    (job.job_id, job.company, job.title, job.location, job.source_url, job.model_dump_json()),
                )
            connection.commit()
        return len(jobs)

    def list_jobs(self) -> list[JobProfile]:
        with connect(self.path) as connection:
            rows = connection.execute("SELECT payload FROM jobs ORDER BY company, title").fetchall()
        return [JobProfile.model_validate_json(row["payload"]) for row in rows]

    def get(self, job_id: str) -> JobProfile | None:
        with connect(self.path) as connection:
            row = connection.execute("SELECT payload FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return JobProfile.model_validate_json(row["payload"]) if row else None

    def count(self) -> int:
        with connect(self.path) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
