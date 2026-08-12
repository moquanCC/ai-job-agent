from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer


class HashingEmbedder:
    """Deterministic offline embedding fallback suitable for demos and tests."""

    def __init__(self, dimensions: int = 512):
        self.vectorizer = HashingVectorizer(n_features=dimensions, analyzer="char", ngram_range=(2, 4), alternate_sign=False, norm="l2")

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.vectorizer.transform(texts).toarray().astype("float32")
