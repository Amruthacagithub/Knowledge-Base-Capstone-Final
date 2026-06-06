from backend import config
from backend.services import embedder, reranker


def test_models_default_to_explicit_cpu_device(monkeypatch):
    embedding_calls = []
    reranker_calls = []

    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(reranker, "_reranker", None)
    monkeypatch.setattr(
        embedder,
        "SentenceTransformer",
        lambda model_name, **kwargs: embedding_calls.append((model_name, kwargs)) or object(),
    )
    monkeypatch.setattr(
        reranker,
        "CrossEncoder",
        lambda model_name, **kwargs: reranker_calls.append((model_name, kwargs)) or object(),
    )

    embedder.get_embedding_model()
    reranker.get_reranker()

    assert config.MODEL_DEVICE == "cpu"
    assert embedding_calls[0][1]["device"] == "cpu"
    assert reranker_calls[0][1]["device"] == "cpu"