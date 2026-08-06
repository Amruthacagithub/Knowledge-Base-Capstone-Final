from backend.services.highlight_match import find_excerpt_range, split_by_excerpts


def test_find_exact():
    content = "The PTO policy allows fifteen days per year."
    r = find_excerpt_range(content, "fifteen days per year")
    assert r is not None
    assert content[r["start"] : r["end"]] == "fifteen days per year"


def test_split_multiple():
    content = "AAAA BBBB CCCC DDDD"
    segs = split_by_excerpts(content, ["BBBB", "DDDD"])
    types = [s["type"] for s in segs]
    assert "highlight" in types
    assert types.count("highlight") == 2


def test_word_sequence_whitespace_tolerant():
    content = "The PTO policy allows\n\nfifteen days per year."
    excerpt = "PTO policy allows fifteen days per year"
    r = find_excerpt_range(content, excerpt)
    assert r is not None
    assert "fifteen" in content[r["start"] : r["end"]]
