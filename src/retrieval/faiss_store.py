from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


class VectorStore:
    def __init__(
        self,
        vectors: np.ndarray | None = None,
        ids: list[str] | None = None,
        metadata: dict | None = None,
    ):
        self.vectors = np.asarray(vectors if vectors is not None else np.empty((0, 0)), dtype="float32")
        self.ids = ids or []
        self.metadata = dict(metadata or {})

    def build(self, vectors: np.ndarray, ids: list[str]) -> None:
        if len(vectors) != len(ids):
            raise ValueError("向量数量与 ID 数量不一致")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        self.vectors = vectors / np.maximum(norms, 1e-12)
        self.ids = list(ids)

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        if not self.ids:
            return []
        q = query.reshape(-1).astype("float32")
        q /= max(float(np.linalg.norm(q)), 1e-12)
        scores = self.vectors @ q
        order = np.argsort(-scores)[:k]
        return [(self.ids[int(i)], float(scores[int(i)])) for i in order]

    def save(self, directory: str | Path, metadata: dict | None = None) -> None:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        if self.vectors.ndim != 2:
            raise ValueError("向量必须是二维数组")
        if len(self.vectors) != len(self.ids):
            raise ValueError("向量数量与 ID 数量不一致")
        persisted_metadata = dict(metadata or self.metadata)
        persisted_metadata.setdefault("backend", "unknown")
        persisted_metadata.setdefault("model", "unknown")
        persisted_metadata.setdefault("normalized", True)
        persisted_metadata.setdefault("built_at", datetime.now(timezone.utc).isoformat())
        persisted_metadata["dimensions"] = int(self.vectors.shape[1])
        persisted_metadata["count"] = len(self.ids)
        np.save(path / "vectors.npy", self.vectors)
        (path / "ids.json").write_text(json.dumps(self.ids, ensure_ascii=False), encoding="utf-8")
        (path / "metadata.json").write_text(
            json.dumps(persisted_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.metadata = persisted_metadata

    @classmethod
    def load(cls, directory: str | Path, expected_model: str | None = None) -> "VectorStore":
        path = Path(directory)
        vectors = np.load(path / "vectors.npy")
        ids = json.loads((path / "ids.json").read_text(encoding="utf-8"))
        metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        if vectors.ndim != 2:
            raise ValueError("索引向量必须是二维数组")
        if len(vectors) != len(ids) or metadata.get("count") != len(ids):
            raise ValueError("索引向量、ID 与元数据记录数量不一致")
        if metadata.get("dimensions") != int(vectors.shape[1]):
            raise ValueError("索引元数据维度与向量维度不一致")
        if expected_model is not None and metadata.get("model") != expected_model:
            raise ValueError(
                f"索引模型不匹配：期望 {expected_model!r}，实际 {metadata.get('model')!r}"
            )
        return cls(vectors, ids, metadata=metadata)
