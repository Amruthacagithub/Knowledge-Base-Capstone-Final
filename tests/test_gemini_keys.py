import pytest

from backend.config import get_gemini_api_keys, get_gemini_models
from backend.services.gemini_client import is_retryable_gemini_error


def test_get_gemini_api_keys_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-one")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-two")
    monkeypatch.setenv("GEMINI_API_KEY_3", "")
    monkeypatch.delenv("GEMINI_API_KEY_4", raising=False)
    keys = get_gemini_api_keys()
    assert keys == ["key-one", "key-two"]


def test_get_gemini_api_keys_dedupes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "same")
    monkeypatch.setenv("GEMINI_API_KEY_2", "same")
    monkeypatch.setenv("GEMINI_API_KEY_3", "")
    monkeypatch.delenv("GEMINI_API_KEY_4", raising=False)
    assert get_gemini_api_keys() == ["same"]


def test_get_gemini_models_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL_FALLBACK", raising=False)
    models = get_gemini_models()
    assert models[0] == "gemini-2.5-flash-lite"
    assert "gemini-3.5-flash" in models
    assert "gemini-2.0-flash" not in models


def test_is_retryable_gemini_error():
    assert is_retryable_gemini_error(Exception("429 RESOURCE_EXHAUSTED quota"))
    assert is_retryable_gemini_error(Exception("Rate limit exceeded"))
    assert is_retryable_gemini_error(Exception("503 UNAVAILABLE high demand"))
    assert not is_retryable_gemini_error(Exception("invalid api key"))
