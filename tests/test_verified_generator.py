from backend.services.generator import generate_verified_answer


class SequencedScorer:
    def __init__(self, batches):
        self.batches = list(batches)

    def score(self, pairs):
        scores = self.batches.pop(0)
        assert len(scores) == len(pairs)
        return scores


def _scores(contradiction, entailment, neutral):
    return {
        "contradiction": contradiction,
        "entailment": entailment,
        "neutral": neutral,
    }


def _chunk(chunk_id, title, text):
    return {
        "chunk_id": chunk_id,
        "doc_id": f"doc-{chunk_id}",
        "doc_title": title,
        "department": "HR",
        "text": text,
        "file_type": "markdown",
    }


def test_verified_generation_renders_only_supported_claims():
    chunks = [_chunk("one", "Leave Policy", "Employees receive 20 PTO days.")]
    scorer = SequencedScorer(
        [[_scores(0.01, 0.98, 0.01), _scores(0.01, 0.98, 0.01)]]
    )

    result = generate_verified_answer(
        "How much PTO is available?",
        chunks,
        text_generator=lambda prompt: (
            '{"claims":[{"text":"Employees receive 20 PTO days.",'
            '"evidence_markers":[1]}]}'
        ),
        scorer=scorer,
    )

    assert "20 PTO days" in result["answer"]
    assert "[1]" in result["answer"]
    assert result["claims"][0]["status"] == "supported"
    assert result["claims"][0]["evidence_ids"] == ["one"]
    assert [citation["marker"] for citation in result["citations"]] == [1]


def test_conflicting_claim_is_withheld_and_answer_abstains():
    chunks = [_chunk("one", "Leave Policy", "Employees receive 20 PTO days.")]
    scorer = SequencedScorer(
        [[_scores(0.98, 0.01, 0.01), _scores(0.98, 0.01, 0.01)]]
    )

    result = generate_verified_answer(
        "How much PTO is available?",
        chunks,
        text_generator=lambda prompt: (
            '{"claims":[{"text":"Employees receive 15 PTO days.",'
            '"evidence_markers":[1]}]}'
        ),
        scorer=scorer,
    )

    assert "15 PTO days" not in result["answer"]
    assert "enough verified information" in result["answer"]
    assert result["claims"][0]["status"] == "conflicting"
    assert result["citations"] == []


def test_malformed_output_falls_back_to_labelled_search_excerpt():
    chunks = [_chunk("one", "Leave Policy", "Employees receive 20 PTO days.")]

    result = generate_verified_answer(
        "How much PTO is available?",
        chunks,
        text_generator=lambda prompt: "PTO is 25 days [1].",
    )

    assert "LLM unavailable" in result["answer"]
    assert "20 PTO days" in result["answer"]
    assert "25 days" not in result["answer"]
    assert result["claims"] == []
    assert [citation["marker"] for citation in result["citations"]] == [1]


def test_one_corrective_retrieval_can_support_insufficient_claim():
    initial = [_chunk("one", "Benefits", "Employees receive paid leave.")]
    corrective = _chunk("two", "Leave Policy", "Employees receive 20 PTO days.")
    scorer = SequencedScorer(
        [
            [_scores(0.01, 0.05, 0.94), _scores(0.01, 0.05, 0.94)],
            [_scores(0.01, 0.98, 0.01), _scores(0.01, 0.98, 0.01)],
        ]
    )
    calls = []

    result = generate_verified_answer(
        "How much PTO is available?",
        initial,
        text_generator=lambda prompt: (
            '{"claims":[{"text":"Employees receive 20 PTO days.",'
            '"evidence_markers":[1]}]}'
        ),
        scorer=scorer,
        corrective_retriever=lambda query: calls.append(query) or [corrective],
    )

    assert len(calls) == 1
    assert result["query_plan"]["corrective_retrieval_used"] is True
    assert result["claims"][0]["status"] == "supported"
    assert result["claims"][0]["evidence_ids"] == ["two"]
    assert result["citations"][0]["marker"] == 2


def test_empty_retrieval_skips_generation():
    result = generate_verified_answer(
        "Question?",
        [],
        text_generator=lambda prompt: (_ for _ in ()).throw(AssertionError()),
    )

    assert result["claims"] == []
    assert result["citations"] == []