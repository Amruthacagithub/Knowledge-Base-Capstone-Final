"""Natural-language inference for claim-level evidence verification."""
from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

from backend.config import MODEL_DEVICE, NLI_MODEL


VerificationLabel = Literal["supported", "conflicting", "insufficient"]
NLI_LABELS = ("contradiction", "entailment", "neutral")


@dataclass(frozen=True)
class VerificationResult:
    label: VerificationLabel
    confidence: float
    evidence_index: int | None
    scores: dict[str, float]


class NLIScorer(Protocol):
    def score(self, pairs: Sequence[tuple[str, str]]) -> list[dict[str, float]]:
        """Return contradiction, entailment, and neutral probabilities."""


class CrossEncoderNLIScorer:
    """Lazy CPU-compatible Sentence Transformers NLI scorer."""

    def __init__(self, model_name: str = NLI_MODEL, device: str = MODEL_DEVICE):
        self.model_name = model_name
        self.device = device
        self._model = None

    def score(self, pairs: Sequence[tuple[str, str]]) -> list[dict[str, float]]:
        if not pairs:
            return []
        model = self._get_model()
        from torch.nn import Softmax

        probabilities = model.predict(
            list(pairs),
            activation_fn=Softmax(dim=1),
            show_progress_bar=False,
        )
        label_by_index = {
            int(index): str(label).lower()
            for index, label in model.model.config.id2label.items()
        }
        if set(label_by_index.values()) != set(NLI_LABELS):
            raise RuntimeError(
                f"NLI model has unsupported labels: {sorted(label_by_index.values())}"
            )
        return [
            {
                label_by_index[index]: float(value)
                for index, value in enumerate(row)
            }
            for row in probabilities
        ]

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            print(f"  Loading NLI verifier: {self.model_name} on {self.device} ...")
            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    @property
    def loaded_device(self) -> str:
        return str(self._get_model().model.device)


_default_scorer: CrossEncoderNLIScorer | None = None


def get_nli_scorer() -> CrossEncoderNLIScorer:
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = CrossEncoderNLIScorer()
    return _default_scorer


def verify_claim(
    claim_text: str,
    evidence_texts: Sequence[str],
    *,
    scorer: NLIScorer | None = None,
    support_threshold: float = 0.75,
    conflict_threshold: float = 0.75,
) -> VerificationResult:
    """Verify one claim against each evidence passage independently."""
    claim = claim_text.strip()
    evidence = [text.strip() for text in evidence_texts if text.strip()]
    if not claim or not evidence:
        return VerificationResult(
            label="insufficient",
            confidence=1.0,
            evidence_index=None,
            scores={"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0},
        )

    pair_scores = (scorer or get_nli_scorer()).score(
        [(passage, claim) for passage in evidence]
        + [(claim, passage) for passage in evidence]
    )
    if len(pair_scores) != len(evidence) * 2:
        raise RuntimeError("NLI scorer returned an unexpected number of results")
    for scores in pair_scores:
        if set(scores) != set(NLI_LABELS):
            raise RuntimeError("NLI scorer returned unsupported labels")

    forward_scores = pair_scores[: len(evidence)]
    reverse_scores = pair_scores[len(evidence) :]
    entailment_index, entailment = _best_score(forward_scores, "entailment")
    contradiction_scores = [
        max(forward["contradiction"], reverse["contradiction"])
        for forward, reverse in zip(forward_scores, reverse_scores)
    ]
    contradiction_index, contradiction = max(
        enumerate(contradiction_scores),
        key=lambda item: item[1],
    )
    neutral_index, neutral = _best_score(forward_scores, "neutral")

    if entailment >= support_threshold and entailment >= contradiction:
        return VerificationResult(
            "supported",
            entailment,
            entailment_index,
            dict(forward_scores[entailment_index]),
        )
    if contradiction >= conflict_threshold:
        return VerificationResult(
            "conflicting",
            contradiction,
            contradiction_index,
            _conflict_scores(
                forward_scores[contradiction_index],
                reverse_scores[contradiction_index],
            ),
        )
    return VerificationResult(
        "insufficient",
        neutral,
        neutral_index,
        dict(forward_scores[neutral_index]),
    )


def _best_score(
    pair_scores: Sequence[dict[str, float]],
    label: str,
) -> tuple[int, float]:
    return max(
        enumerate(float(scores[label]) for scores in pair_scores),
        key=lambda item: item[1],
    )


def _conflict_scores(
    forward: dict[str, float],
    reverse: dict[str, float],
) -> dict[str, float]:
    return {
        "contradiction": max(forward["contradiction"], reverse["contradiction"]),
        "entailment": forward["entailment"],
        "neutral": forward["neutral"],
    }