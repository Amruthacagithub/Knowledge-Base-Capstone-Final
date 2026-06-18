from backend.services.generator import parse_citations, _fallback_citations, _fallback_answer_text


def _chunk(doc_id, title, text):
    return {
        "doc_id": doc_id,
        "doc_title": title,
        "department": "HR",
        "text": text,
        "file_type": "markdown",
    }


def test_parse_citations_from_markers():
    chunks = [_chunk("1", "Leave Policy", "PTO cannot be cashed out.")]
    answer = "Employees get 20 days [1]."
    cites = parse_citations(answer, chunks)
    assert len(cites) == 1
    assert cites[0]["marker"] == 1
    assert "cash" in cites[0]["chunk_text"].lower()


def test_fallback_when_no_markers():
    chunks = [
        _chunk("1", "Leave Policy", "PTO text"),
        _chunk("2", "Leave Policy (PDF)", "Same policy PDF"),
        _chunk("3", "Handbook", "Handbook text"),
    ]
    cites = parse_citations("Answer without citation markers.", chunks)
    assert cites == []


def test_fallback_answer_includes_markers():
    chunks = [_chunk("1", "Leave Policy", "PTO cannot be cashed out.")]
    text = _fallback_answer_text("PTO?", chunks, "429 quota")
    assert "[1]" in text
    assert "429 quota" not in text
    assert "quota" in text.lower()
    cites = parse_citations(text, chunks)
    assert len(cites) >= 1
