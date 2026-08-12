from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/app.db"
    default_location: str = "上海"
    top_k: int = 10
    embedding_model: str = "local-hashing-v1"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            default_location=os.getenv("DEFAULT_LOCATION", cls.default_location),
            top_k=int(os.getenv("TOP_K", str(cls.top_k))),
            embedding_model=os.getenv("EMBEDDING_MODEL", cls.embedding_model),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_base_url=os.getenv("LLM_BASE_URL", ""),
            llm_model=os.getenv("LLM_MODEL", ""),
        )


def load_yaml(relative_path: str) -> dict:
    with (ROOT / relative_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def database_path(url: str) -> Path:
    prefix = "sqlite:///"
    value = url[len(prefix):] if url.startswith(prefix) else url
    path = Path(value)
    return path if path.is_absolute() else ROOT / path
