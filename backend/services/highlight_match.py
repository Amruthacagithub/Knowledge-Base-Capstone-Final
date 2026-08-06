"""Highlight excerpt matching (mirrors frontend highlightContent.js)."""
import re

from backend.services.highlight_excerpt import excerpt_for_highlight


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def build_highlight_needles(excerpt: str) -> list[str]:
    if not excerpt or not excerpt.strip():
        return []

    text = excerpt.strip()
    needles: set[str] = set()

    def add(value: str | None) -> None:
        if value and value.strip():
            needles.add(value.strip())

    add(text)
    add(excerpt_for_highlight(text, 800))
    add(excerpt_for_highlight(text, 480))

    stripped = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE).strip()
    if stripped != text:
        add(stripped)
        add(excerpt_for_highlight(stripped, 480))

    for length in (400, 300, 200, 120, 80, 50):
        if len(text) >= length:
            add(text[:length])

    return sorted(needles, key=len, reverse=True)


def _find_by_word_sequence(content: str, excerpt: str) -> dict | None:
    words = [w for w in _normalize(excerpt).split(" ") if len(w) > 1]
    if len(words) < 4:
        return None

    pattern = r"\s+".join(re.escape(w) for w in words)
    match = re.search(pattern, content, flags=re.IGNORECASE)
    if not match:
        return None
    return {"start": match.start(), "end": match.end(), "needle": match.group(0)}


def find_excerpt_range(content: str, excerpt: str) -> dict | None:
    if not content or not excerpt or not excerpt.strip():
        return None

    for needle in build_highlight_needles(excerpt):
        result = _find_excerpt_range_once(content, needle)
        if result:
            return result
    return None


def _find_excerpt_range_once(content: str, excerpt: str) -> dict | None:
    needle = excerpt.strip()
    idx = content.find(needle)

    if idx == -1:
        n_needle = _normalize(needle)
        n_content = _normalize(content)
        if n_needle and n_needle in n_content and len(n_needle) >= 40:
            word = _find_by_word_sequence(content, n_needle)
            if word:
                return word

        for length in (300, 200, 120, 80, 50):
            if len(needle) >= length:
                short = needle[:length]
                idx = content.find(short)
                if idx != -1:
                    return {"start": idx, "end": idx + len(short), "needle": short}
                word = _find_by_word_sequence(content, short)
                if word:
                    return word
        return _find_by_word_sequence(content, needle)

    return {"start": idx, "end": idx + len(needle), "needle": needle}


def split_by_excerpts(content: str, excerpts: list[str]) -> list[dict]:
    if not content:
        return [{"type": "normal", "text": ""}]

    needles: list[str] = []
    for excerpt in excerpts:
        if excerpt and str(excerpt).strip():
            needles.extend(build_highlight_needles(str(excerpt)))

    unique = []
    seen = set()
    for n in needles:
        if n not in seen:
            seen.add(n)
            unique.append(n)

    ranges = []
    for needle in unique:
        r = _find_excerpt_range_once(content, needle)
        if r:
            ranges.append(r)
        else:
            r = _find_by_word_sequence(content, needle)
            if r:
                ranges.append(r)

    if not ranges:
        return [{"type": "normal", "text": content}]

    ranges.sort(key=lambda x: x["start"])
    merged = []
    for r in ranges:
        if not merged or r["start"] > merged[-1]["end"]:
            merged.append(dict(r))
        else:
            merged[-1]["end"] = max(merged[-1]["end"], r["end"])

    segments = []
    pos = 0
    for r in merged:
        if r["start"] > pos:
            segments.append({"type": "normal", "text": content[pos : r["start"]]})
        segments.append({"type": "highlight", "text": content[r["start"] : r["end"]]})
        pos = r["end"]
    if pos < len(content):
        segments.append({"type": "normal", "text": content[pos:]})
    return segments
