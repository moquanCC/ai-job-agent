from __future__ import annotations

import json
from pathlib import Path

from src.repositories.database import connect, initialize


class AnalysisRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        with connect(self.path) as connection:
            initialize(connection)

    def save(self, candidate_id: str, job_id: str, payload: dict) -> int:
        with connect(self.path) as connection:
            cursor = connection.execute(
                "INSERT INTO analyses(candidate_id, job_id, payload) VALUES (?, ?, ?)",
                (candidate_id, job_id, json.dumps(payload, ensure_ascii=False)),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def delete_candidate(self, candidate_id: str) -> int:
        with connect(self.path) as connection:
            cursor = connection.execute("DELETE FROM analyses WHERE candidate_id=?", (candidate_id,))
            connection.commit()
            return cursor.rowcount
