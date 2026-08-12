from __future__ import annotations

import numpy as np

from src.config import Settings
from src.services.analysis_service import AnalysisService


class FakeEmbedder:
    name = "fake-embedding-v1"
    fallback_occurred = False

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 3), dtype=np.float32)


def test_analysis_service_preserves_injected_embedder(tmp_path) -> None:
    embedder = FakeEmbedder()

    service = AnalysisService(db_path=tmp_path / "app.db", embedder=embedder)

    assert service.embedder is embedder
    assert service.embedding_status == {
        "requested_backend": "auto",
        "actual_backend": "fake-embedding-v1",
        "model": "fake-embedding-v1",
        "fallback_occurred": False,
    }


def test_analysis_service_creates_lazy_auto_embedder_once(monkeypatch, tmp_path) -> None:
    created: list[dict] = []
    embedder = FakeEmbedder()

    def fake_create_embedder(backend: str, **kwargs):
        created.append({"backend": backend, **kwargs})
        return embedder

    monkeypatch.setattr("src.services.analysis_service.create_embedder", fake_create_embedder)
    settings = Settings(
        embedding_backend="auto",
        embedding_model="BAAI/bge-m3",
        embedding_device="cpu",
        embedding_batch_size=4,
        embedding_max_length=512,
    )

    service = AnalysisService(settings=settings, db_path=tmp_path / "app.db")

    assert service.embedder is embedder
    assert created == [
        {
            "backend": "auto",
            "model_name": "BAAI/bge-m3",
            "device": "cpu",
            "batch_size": 4,
            "max_length": 512,
        }
    ]

