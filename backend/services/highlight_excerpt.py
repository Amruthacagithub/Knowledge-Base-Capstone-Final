"""Excerpt helpers for highlight matching (mirrors frontend citationExcerpt.js)."""


def excerpt_for_highlight(chunk_text: str, max_len: int = 480) -> str | None:
    if not chunk_text or not chunk_text.strip():
        return None
    text = chunk_text.strip()
    if len(text) <= max_len:
        return text

    cut = text[:max_len]
    sentence_end = max(
        cut.rfind(". "),
        cut.rfind(".\n"),
        cut.rfind("! "),
        cut.rfind("? "),
    )
    if sentence_end > 60:
        return cut[: sentence_end + 1].strip()

    word_cut = cut.rfind(" ")
    if word_cut > 40:
        return cut[:word_cut].strip()
    return cut.strip()
