from __future__ import annotations

from typing import Any, Protocol

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer


class TextEmbedder(Protocol):
    """Minimal interface shared by local and model-backed embedders."""

    @property
    def name(self) -> str: ...

    def encode(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder:
    """Deterministic offline embedding fallback suitable for demos and tests."""

    def __init__(self, dimensions: int = 512):
        if not isinstance(dimensions, int) or isinstance(dimensions, bool) or dimensions <= 0:
            raise ValueError("dimensions 必须是正整数")
        self.dimensions = dimensions
        self.vectorizer = HashingVectorizer(
            n_features=dimensions,
            analyzer="char",
            ngram_range=(2, 4),
            alternate_sign=False,
            norm="l2",
        )

    @property
    def name(self) -> str:
        return "local-hashing-v1"

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimensions), dtype=np.float32)
        return self.vectorizer.transform(texts).toarray().astype("float32")


class BgeM3Embedder:
    """Lazy SentenceTransformer adapter for normalized BGE-M3 dense vectors."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 8,
        max_length: int = 1024,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name 不能为空")
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
            raise ValueError("batch_size 必须是正整数")
        if not isinstance(max_length, int) or isinstance(max_length, bool) or max_length <= 0:
            raise ValueError("max_length 必须是正整数")
        if device is not None and not isinstance(device, str):
            raise ValueError("device 必须是字符串或 None")

        self.model_name = model_name.strip()
        self.batch_size = batch_size
        self.max_length = max_length
        self.device = device or None
        self._model = model
        self._dimensions: int | None = None
        if self._model is not None:
            self._model.max_seq_length = self.max_length

    @property
    def name(self) -> str:
        return self.model_name

    @property
    def dimensions(self) -> int | None:
        return self._dimensions

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
            self._model.max_seq_length = self.max_length
            return self._model
        except Exception as exc:
            raise RuntimeError(
                "BGE-M3 不可用；请安装 `pip install -e .[embedding]` 并预下载 "
                "BAAI/bge-m3，或设置 EMBEDDING_BACKEND=hashing"
            ) from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            if self._dimensions is None:
                raise ValueError("首次编码不能使用空文本批次；模型维度尚未知")
            return np.empty((0, self._dimensions), dtype=np.float32)

        model = self._load_model()
        vectors = np.asarray(
            model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        if vectors.ndim != 2 or vectors.shape[0] != len(texts):
            raise ValueError("BGE-M3 返回了无效的二维向量形状")
        if not np.all(np.isfinite(vectors)):
            raise ValueError("BGE-M3 返回了非有限向量")

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError("BGE-M3 返回了无法归一化的零向量")
        vectors = np.asarray(vectors / norms, dtype=np.float32)
        self._dimensions = int(vectors.shape[1])
        return vectors


class AutoEmbedder:
    """Prefer BGE-M3, then expose and use the hashing backend after load failure."""

    def __init__(self, bge: BgeM3Embedder, fallback: HashingEmbedder) -> None:
        self._bge = bge
        self._fallback = fallback
        self._selected: TextEmbedder | None = None
        self.fallback_occurred = False

    @property
    def name(self) -> str:
        if self._selected is None:
            return "auto"
        return self._selected.name

    @property
    def dimensions(self) -> int | None:
        if self._selected is None:
            return None
        return getattr(self._selected, "dimensions", None)

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._selected is None:
            try:
                self._bge._load_model()
            except RuntimeError:
                self._selected = self._fallback
                self.fallback_occurred = True
            else:
                self._selected = self._bge
        return self._selected.encode(texts)


def create_embedder(
    backend: str,
    *,
    model_name: str = "BAAI/bge-m3",
    batch_size: int = 8,
    max_length: int = 1024,
    device: str | None = None,
    model: Any | None = None,
    dimensions: int = 512,
) -> TextEmbedder:
    """Create an embedder without importing or downloading BGE-M3 eagerly."""

    normalized_backend = backend.strip().lower() if isinstance(backend, str) else ""
    if normalized_backend == "hashing":
        return HashingEmbedder(dimensions=dimensions)

    if normalized_backend in {"bge-m3", "auto"}:
        bge = BgeM3Embedder(
            model_name=model_name,
            batch_size=batch_size,
            max_length=max_length,
            device=device,
            model=model,
        )
        if normalized_backend == "bge-m3":
            return bge
        return AutoEmbedder(bge=bge, fallback=HashingEmbedder(dimensions=dimensions))

    raise ValueError(
        f"不支持的 embedding backend: {backend!r}；可选值为 hashing、bge-m3、auto"
    )
