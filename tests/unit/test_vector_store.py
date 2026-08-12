from __future__ import annotations

import json

import numpy as np
import pytest

from src.retrieval.faiss_store import VectorStore


def test_vector_store_persists_model_metadata(tmp_path) -> None:
    store = VectorStore()
    store.build(np.array([[3.0, 4.0], [1.0, 0.0]], dtype=np.float32), ["a", "b"])

    store.save(tmp_path, metadata={"backend": "bge-m3", "model": "BAAI/bge-m3"})

    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["backend"] == "bge-m3"
    assert metadata["model"] == "BAAI/bge-m3"
    assert metadata["dimensions"] == 2
    assert metadata["count"] == 2
    loaded = VectorStore.load(tmp_path, expected_model="BAAI/bge-m3")
    assert loaded.metadata == metadata


def test_vector_store_rejects_expected_model_mismatch(tmp_path) -> None:
    store = VectorStore(np.ones((1, 2), dtype=np.float32), ["a"])
    store.save(tmp_path, metadata={"backend": "bge-m3", "model": "BAAI/bge-m3"})

    with pytest.raises(ValueError, match="模型不匹配"):
        VectorStore.load(tmp_path, expected_model="local-hashing-v1")


def test_vector_store_load_validates_vector_and_id_count(tmp_path) -> None:
    store = VectorStore(np.ones((2, 3), dtype=np.float32), ["a", "b"])
    store.save(tmp_path, metadata={"backend": "hashing", "model": "local-hashing-v1"})
    (tmp_path / "ids.json").write_text('["a"]', encoding="utf-8")

    with pytest.raises(ValueError, match="数量"):
        VectorStore.load(tmp_path)


def test_vector_store_load_validates_metadata_dimensions(tmp_path) -> None:
    store = VectorStore(np.ones((1, 3), dtype=np.float32), ["a"])
    store.save(tmp_path, metadata={"backend": "hashing", "model": "local-hashing-v1"})
    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    metadata["dimensions"] = 4
    (tmp_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="维度"):
        VectorStore.load(tmp_path)

