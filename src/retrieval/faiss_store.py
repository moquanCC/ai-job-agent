from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class VectorStore:
    def __init__(self, vectors: np.ndarray | None = None, ids: list[str] | None = None):
        self.vectors = np.asarray(vectors if vectors is not None else np.empty((0, 0)), dtype="float32")
        self.ids = ids or []

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

    def save(self, directory: str | Path) -> None:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        np.save(path / "vectors.npy", self.vectors)
        (path / "ids.json").write_text(json.dumps(self.ids, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, directory: str | Path) -> "VectorStore":
        path = Path(directory)
        return cls(np.load(path / "vectors.npy"), json.loads((path / "ids.json").read_text(encoding="utf-8")))
