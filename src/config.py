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
    embedding_backend: str = "auto"
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = ""
    embedding_batch_size: int = 8
    embedding_max_length: int = 1024
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    def __post_init__(self) -> None:
        if self.embedding_backend not in {"auto", "bge-m3", "hashing"}:
            raise ValueError("embedding_backend 必须是 auto、bge-m3 或 hashing")
        if not isinstance(self.embedding_batch_size, int) or isinstance(self.embedding_batch_size, bool) or self.embedding_batch_size <= 0:
            raise ValueError("embedding_batch_size 必须是正整数")
        if not isinstance(self.embedding_max_length, int) or isinstance(self.embedding_max_length, bool) or self.embedding_max_length <= 0:
            raise ValueError("embedding_max_length 必须是正整数")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            default_location=os.getenv("DEFAULT_LOCATION", cls.default_location),
            top_k=int(os.getenv("TOP_K", str(cls.top_k))),
            embedding_backend=os.getenv("EMBEDDING_BACKEND", cls.embedding_backend).strip().lower(),
            embedding_model=os.getenv("EMBEDDING_MODEL", cls.embedding_model),
            embedding_device=os.getenv("EMBEDDING_DEVICE", cls.embedding_device).strip(),
            embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", str(cls.embedding_batch_size))),
            embedding_max_length=int(os.getenv("EMBEDDING_MAX_LENGTH", str(cls.embedding_max_length))),
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
