import pytest

from backend.services.claim_verifier import verify_claim


class FakeScorer:
    def __init__(self, scores):
        self.scores = scores
        self.pairs = None

    def score(self, pairs):
        self.pairs = list(pairs)
        return self.scores


def _scores(contradiction, entailment, neutral):
    return {
        "contradiction": contradiction,
        "entailment": entailment,
        "neutral": neutral,
    }


def test_supported_claim_selects_entailing_evidence():
    scorer = FakeScorer(
        [
            _scores(0.01, 0.05, 0.94),
            _scores(0.01, 0.97, 0.02),
            _scores(0.01, 0.05, 0.94),
            _scores(0.01, 0.97, 0.02),
        ]
    )

    result = verify_claim("PTO is 20 days.", ["Other text.", "PTO is 20 days."], scorer=scorer)

    assert result.label == "supported"
    assert result.evidence_index == 1
    assert result.confidence == pytest.approx(0.97)
    assert scorer.pairs[1] == ("PTO is 20 days.", "PTO is 20 days.")


def test_conflicting_claim_selects_contradicting_evidence():
    scorer = FakeScorer(
        [_scores(0.10, 0.01, 0.89), _scores(0.96, 0.01, 0.03)]
    )

    result = verify_claim("PTO is 15 days.", ["PTO is 20 days."], scorer=scorer)

    assert result.label == "conflicting"
    assert result.evidence_index == 0


def test_uncertain_claim_is_insufficient():
    scorer = FakeScorer(
        [_scores(0.20, 0.30, 0.50), _scores(0.20, 0.30, 0.50)]
    )

    result = verify_claim("Backups last 30 days.", ["Backups run daily."], scorer=scorer)

    assert result.label == "insufficient"
    assert result.confidence == pytest.approx(0.50)


def test_empty_evidence_abstains_without_loading_scorer():
    result = verify_claim("PTO is 20 days.", [], scorer=FakeScorer([]))

    assert result.label == "insufficient"
    assert result.evidence_index is None


def test_scorer_must_return_all_three_labels():
    scorer = FakeScorer([{"entailment": 1.0}, {"entailment": 1.0}])

    with pytest.raises(RuntimeError, match="unsupported labels"):
        verify_claim("Claim.", ["Evidence."], scorer=scorer)