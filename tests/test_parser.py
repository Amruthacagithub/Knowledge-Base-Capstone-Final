from backend.services.parser import parse_document


def test_parse_markdown(sample_md):
    segments = parse_document(sample_md)
    assert len(segments) >= 1
    assert "Hello world" in segments[0]["text"]
    assert segments[0]["page"] == 1


def test_parse_pdf(sample_pdf):
    segments = parse_document(sample_pdf)
    assert len(segments) == 2
    assert segments[0]["page"] == 1
    assert "PTO" in segments[0]["text"]
    assert segments[1]["page"] == 2
