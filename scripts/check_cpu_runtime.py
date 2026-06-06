"""Verify that all local retrieval models execute without CUDA or a GPU."""
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "cpu-runtime-check-only-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch

from backend.config import CLAIM_VERIFICATION_ENABLED, MODEL_DEVICE
from backend.services.claim_verifier import CrossEncoderNLIScorer
from backend.services.embedder import get_embedding_model
from backend.services.reranker import get_reranker


def main() -> int:
    if MODEL_DEVICE != "cpu":
        print(f"FAIL: MODEL_DEVICE is {MODEL_DEVICE!r}; expected 'cpu'.")
        return 1

    embedding_model = get_embedding_model()
    reranker = get_reranker()
    embedding = embedding_model.encode(["Trust-RAG CPU runtime check"])
    rerank_scores = reranker.predict([("What device is used?", "CPU inference")])

    embedding_device = str(embedding_model.device)
    reranker_device = str(reranker.model.device)
    nli_device = None
    if CLAIM_VERIFICATION_ENABLED:
        nli_scorer = CrossEncoderNLIScorer()
        nli_scorer.score(
            [("The system runs on CPU.", "The system uses CPU inference.")]
        )
        nli_device = nli_scorer.loaded_device

    if (
        embedding_device != "cpu"
        or reranker_device != "cpu"
        or (nli_device is not None and nli_device != "cpu")
    ):
        print(
            "FAIL: models are not on CPU "
            f"(embedding={embedding_device}, reranker={reranker_device}, "
            f"nli={nli_device or 'disabled'})."
        )
        return 1

    print(
        "PASS: CPU-only inference verified "
        f"(torch={torch.__version__}, cuda_available={torch.cuda.is_available()}, "
        f"embedding_shape={tuple(embedding.shape)}, "
        f"rerank_shape={tuple(rerank_scores.shape)}, "
        f"nli={nli_device or 'disabled'})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())