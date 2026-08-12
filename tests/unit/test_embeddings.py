from __future__ import annotations

import numpy as np
import pytest

from src.retrieval.embeddings import (
    AutoEmbedder,
    BgeM3Embedder,
    HashingEmbedder,
    create_embedder,
)


class FakeModel:
    def __init__(self) -> None:
        self.max_seq_length = None
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def encode(self, texts: list[str], **kwargs: object) -> np.ndarray:
        self.calls.append((texts, kwargs))
        return np.array([[3.0, 4.0], [0.0, 2.0]], dtype="float64")


def test_bge_adapter_batches_normalizes_and_uses_float32() -> None:
    model = FakeModel()
    embedder = BgeM3Embedder(model=model, batch_size=8, max_length=1024)

    vectors = embedder.encode(["中文简历", "上海算法岗位"])

    assert vectors.dtype == np.float32
    assert vectors.shape == (2, 2)
    assert np.linalg.norm(vectors, axis=1) == pytest.approx([1, 1])
    assert model.max_seq_length == 1024
    assert model.calls[0][0] == ["中文简历", "上海算法岗位"]
    assert model.calls[0][1]["batch_size"] == 8
    assert model.calls[0][1]["normalize_embeddings"] is True


def test_bge_adapter_reuses_injected_model_and_tracks_dimensions() -> None:
    model = FakeModel()
    embedder = BgeM3Embedder(model=model)

    embedder.encode(["a", "b"])

    assert embedder.name == "BAAI/bge-m3"
    assert embedder.dimensions == 2
    assert embedder.encode([]).shape == (0, 2)
    assert model.calls == [model.calls[0]]


def test_bge_empty_input_requires_known_dimensions() -> None:
    with pytest.raises(ValueError, match="空文本批次"):
        BgeM3Embedder(model=FakeModel()).encode([])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model_name": ""}, "model_name"),
        ({"batch_size": 0}, "batch_size"),
        ({"max_length": -1}, "max_length"),
        ({"device": 1}, "device"),
    ],
)
def test_bge_rejects_invalid_parameters(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BgeM3Embedder(**kwargs)


def test_hashing_embedder_keeps_compatible_normalized_output() -> None:
    embedder = HashingEmbedder(dimensions=32)
    vectors = embedder.encode(["中文简历", "算法岗位"])

    assert embedder.name == "local-hashing-v1"
    assert embedder.dimensions == 32
    assert vectors.dtype == np.float32
    assert vectors.shape == (2, 32)
    assert np.linalg.norm(vectors, axis=1) == pytest.approx([1, 1])
    assert embedder.encode([]).shape == (0, 32)


def test_hashing_rejects_nonpositive_dimensions() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        HashingEmbedder(dimensions=0)


def test_create_embedder_supports_all_backends_without_loading_bge() -> None:
    assert isinstance(create_embedder("hashing"), HashingEmbedder)
    assert isinstance(create_embedder("bge-m3", model=FakeModel()), BgeM3Embedder)
    assert isinstance(create_embedder("auto", model=FakeModel()), AutoEmbedder)


def test_create_embedder_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="不支持的 embedding backend"):
        create_embedder("unknown")


def test_auto_uses_bge_when_available() -> None:
    embedder = create_embedder("auto", model=FakeModel(), dimensions=16)

    vectors = embedder.encode(["a", "b"])

    assert vectors.shape == (2, 2)
    assert embedder.name == "BAAI/bge-m3"
    assert embedder.fallback_occurred is False


def test_auto_falls_back_only_when_bge_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = create_embedder("auto", dimensions=16)

    def unavailable() -> object:
        raise RuntimeError("BGE-M3 不可用")

    monkeypatch.setattr(embedder._bge, "_load_model", unavailable)
    vectors = embedder.encode(["中文简历"])

    assert vectors.shape == (1, 16)
    assert embedder.name == "local-hashing-v1"
    assert embedder.fallback_occurred is True


def test_explicit_bge_propagates_actionable_loading_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedder = create_embedder("bge-m3")

    def unavailable() -> object:
        raise RuntimeError(
            "BGE-M3 不可用；请安装 `pip install -e .[embedding]` 并预下载 "
            "BAAI/bge-m3，或设置 EMBEDDING_BACKEND=hashing"
        )

    monkeypatch.setattr(embedder, "_load_model", unavailable)
    with pytest.raises(RuntimeError, match="pip install -e"):
        embedder.encode(["中文简历"])
