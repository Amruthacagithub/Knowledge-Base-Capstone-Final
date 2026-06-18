"""
Query router — classifies queries to tune hybrid search weights.
"""
import re
from typing import Literal

QueryType = Literal["conceptual", "specific"]
TemporalIntent = Literal["none", "current", "historical", "change"]

# Error codes, incident IDs, version numbers, quoted phrases
_SPECIFIC_PATTERNS = [
    re.compile(r"\b(?:error|code|incident)[ #\t]*\d{3,5}\b", re.I),
    re.compile(r"\bINC-\d+\b", re.I),
    re.compile(r"\b\d{3,5}\b"),  # standalone numeric codes like 5023
    re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b"),  # version numbers
    re.compile(r'"[^"]+"'),  # quoted exact phrase
    re.compile(r"\btech\s*stack\b", re.I),
]

# Acronyms in ALL CAPS (exclude common policy terms asked conceptually)
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")
_COMMON_ACRONYMS = frozenset({"PTO", "HR", "IT", "FAQ", "CEO", "VP", "OKR", "EEO"})

_TEMPORAL_CHANGE_PATTERNS = (
    re.compile(r"\bwhat\s+changed\b", re.I),
    re.compile(r"\bhow\s+(?:has|did)\b.*\bchange", re.I),
    re.compile(r"\b(?:compare|difference\s+between)\b.*\bversions?\b", re.I),
    re.compile(r"\bchanged\s+since\b", re.I),
    re.compile(r"\b(?:old|previous)\b.*\b(?:new|current)\b", re.I),
)
_TEMPORAL_HISTORICAL_PATTERNS = (
    re.compile(r"\bas\s+of\b", re.I),
    re.compile(r"\b(?:historical|previous\s+version|old\s+policy)\b", re.I),
    re.compile(r"\b(?:before|during|at\s+the\s+time)\b", re.I),
    re.compile(r"\bin\s+(?:19|20)\d{2}\b", re.I),
    re.compile(r"\bon\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", re.I),
)
_TEMPORAL_CURRENT_PATTERNS = (
    re.compile(r"\b(?:current|latest|most\s+recent)\b", re.I),
    re.compile(r"\b(?:now|today|currently)\b", re.I),
    re.compile(r"\b(?:in\s+effect|effective\s+policy)\b", re.I),
)


def classify_query(query: str) -> QueryType:
    """
    Classify query as conceptual (broad) or specific (exact terms/codes).

    Specific queries get higher BM25 weight in hybrid fusion.
    """
    q = query.strip()
    if not q:
        return "conceptual"

    for pattern in _SPECIFIC_PATTERNS:
        if pattern.search(q):
            return "specific"

    for match in _ACRONYM_RE.finditer(q):
        if match.group() not in _COMMON_ACRONYMS:
            return "specific"

    # Short keyword-heavy queries
    words = q.split()
    if len(words) <= 5 and any(
        w.lower() in ("stack", "api", "inc", "error", "5023", "salesforce", "postgresql")
        for w in words
    ):
        return "specific"

    return "conceptual"


def alpha_for_query_type(query_type: QueryType) -> float:
    """Vector weight (alpha); remainder goes to BM25."""
    if query_type == "specific":
        return 0.48
    return 0.68


def classify_temporal_intent(query: str) -> TemporalIntent:
    """Classify explicit temporal intent without changing hybrid query routing."""
    normalized = " ".join(query.split())
    if not normalized:
        return "none"
    for intent, patterns in (
        ("change", _TEMPORAL_CHANGE_PATTERNS),
        ("historical", _TEMPORAL_HISTORICAL_PATTERNS),
        ("current", _TEMPORAL_CURRENT_PATTERNS),
    ):
        if any(pattern.search(normalized) for pattern in patterns):
            return intent
    return "none"
