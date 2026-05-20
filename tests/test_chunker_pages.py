from backend.services.chunker import chunk_document_segments, chunk_text


def test_chunks_preserve_page():
    segments = [
        {"text": "Alpha " * 80, "page": 1},
        {"text": "Beta " * 80, "page": 2},
    ]
    chunks = chunk_document_segments(segments, max_tokens=50, overlap_tokens=5)
    assert all("page_start" in c and "page_end" in c for c in chunks)
    pages = {c["page_start"] for c in chunks}
    assert 1 in pages
    assert 2 in pages


def test_single_page_markdown():
    segments = [{"text": "Short doc.", "page": 1}]
    chunks = chunk_document_segments(segments)
    assert len(chunks) == 1
    assert chunks[0]["page_start"] == 1


def test_chunk_text_preserves_markdown_paragraphs_and_lines():
    text = (
        "## Dependency Map\n"
        "Clients → Kong Gateway → User Service\n"
        "         → Billing Service → Stripe\n\n"
        "## Notes\n"
        "Each row is a separate path."
    )

    assert chunk_text(text) == [text]
