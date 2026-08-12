from __future__ import annotations

import pytest

from src.config import Settings


def test_embedding_settings_defaults() -> None:
    settings = Settings()

    assert settings.embedding_backend == "auto"
    assert settings.embedding_model == "BAAI/bge-m3"
    assert settings.embedding_device == ""
    assert settings.embedding_batch_size == 8
    assert settings.embedding_max_length == 1024


def test_embedding_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_BACKEND", "bge-m3")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    monkeypatch.setenv("EMBEDDING_DEVICE", "cpu")
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "4")
    monkeypatch.setenv("EMBEDDING_MAX_LENGTH", "512")

    settings = Settings.from_env()

    assert settings.embedding_backend == "bge-m3"
    assert settings.embedding_model == "BAAI/bge-m3"
    assert settings.embedding_device == "cpu"
    assert settings.embedding_batch_size == 4
    assert settings.embedding_max_length == 512


@pytest.mark.parametrize("backend", ["unknown", "", "bge"])
def test_embedding_settings_reject_unknown_backend(backend: str) -> None:
    with pytest.raises(ValueError, match="embedding_backend"):
        Settings(embedding_backend=backend)


@pytest.mark.parametrize(
    ("field", "value"),
    [("embedding_batch_size", 0), ("embedding_batch_size", -1), ("embedding_max_length", 0)],
)
def test_embedding_settings_reject_nonpositive_numbers(field: str, value: int) -> None:
    with pytest.raises(ValueError, match=field):
        Settings(**{field: value})

