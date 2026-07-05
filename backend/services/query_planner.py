"""Deterministic, bounded routing for Trust-RAG retrieval strategies."""
import re
from dataclasses import dataclass
from typing import Literal, Sequence

from backend.services.query_router import classify_temporal_intent


PlannerRoute = Literal["local", "global", "multi_hop", "temporal", "comparison"]
MAX_SUBQUERIES = 4
MAX_SUBQUERY_CHARS = 300

_COMPARISON_PATTERNS = (
    re.compile(r"\bcompare\b", re.I),
    re.compile(r"\b(?:versus|vs[.]?)\b", re.I),
    re.compile(r"\bdifferences?\s+between\b", re.I),
    re.compile(r"\bcontrast\b", re.I),
    re.compile(r"\bside[- ]by[- ]side\b", re.I),
    re.compile(r"\bhow\s+do\b.{0,120}\bdiffer\b", re.I),
    re.compile(r"\bsimilarities\s+and\s+differences\b", re.I),
    re.compile(r"\bwhich\s+is\s+(?:stricter|safer|faster)\b", re.I),
)
_MULTI_HOP_PATTERNS = (
    re.compile(r"\b(?:dependency|service)\s+(?:chain|path)\b", re.I),
    re.compile(r"\b(?:downstream|transitively)\b", re.I),
    re.compile(r"\bdepends?\s+on\b", re.I),
    re.compile(r"\blie\s+between\b", re.I),
    re.compile(r"\bconnected\s+through\b", re.I),
    re.compile(r"\broute\s+from\b", re.I),
    re.compile(r"\bultimately\s+reach\b", re.I),
    re.compile(r"\b(?:impacted|affected)\b", re.I),
)
_GLOBAL_PATTERNS = (
    re.compile(r"\b(?:organization|enterprise)[- ]wide\b", re.I),
    re.compile(r"\bacross\s+all\b", re.I),
    re.compile(r"\bentire\s+document\s+collection\b", re.I),
    re.compile(r"\bbroad\s+overview\b", re.I),
    re.compile(r"\bhigh[- ]level\s+summary\s+of\s+all\b", re.I),
    re.compile(r"\brecurring\s+themes\b", re.I),
    re.compile(r"\bthroughout\s+the\s+corpus\b", re.I),
    re.compile(r"\bwhole\s+knowledge\s+base\b", re.I),
    re.compile(r"\bsummarize\s+everything\b", re.I),
)


@dataclass(frozen=True)
class QueryPlan:
    route: PlannerRoute
    subqueries: tuple[str, ...]


def plan_query(
    query: str,
    *,
    proposed_subqueries: Sequence[str] = (),
) -> QueryPlan:
    """Choose one route with explicit deterministic precedence."""
    normalized = " ".join(query.split())
    route = classify_planner_route(normalized)
    subqueries = proposed_subqueries or derive_subqueries(normalized, route)
    return QueryPlan(
        route=route,
        subqueries=validate_subqueries(subqueries),
    )


def classify_planner_route(query: str) -> PlannerRoute:
    normalized = " ".join(query.split())
    if classify_temporal_intent(normalized) != "none":
        return "temporal"
    if _matches_any(normalized, _COMPARISON_PATTERNS):
        return "comparison"
    if _matches_any(normalized, _MULTI_HOP_PATTERNS):
        return "multi_hop"
    if _matches_any(normalized, _GLOBAL_PATTERNS):
        return "global"
    return "local"


def validate_subqueries(subqueries: Sequence[str]) -> tuple[str, ...]:
    """Bound, normalize, and deduplicate optional planner subqueries."""
    validated = []
    seen = set()
    for candidate in subqueries:
        if not isinstance(candidate, str):
            continue
        normalized = " ".join(candidate.split())[:MAX_SUBQUERY_CHARS].strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        validated.append(normalized)
        if len(validated) >= MAX_SUBQUERIES:
            break
    return tuple(validated)


def derive_subqueries(query: str, route: PlannerRoute) -> list[str]:
    """Derive conservative retrieval fan-out for routes that benefit from coverage."""
    if route == "global":
        return ["HR policies", "Engineering systems", "Sales operations"]
    if route == "comparison":
        return _comparison_subjects(query)
    if route == "multi_hop":
        return _path_endpoints(query)
    return []


def _comparison_subjects(query: str) -> list[str]:
    patterns = (
        re.compile(
            r"\b(?:compare|contrast)\s+(.{1,120}?)\s+"
            r"(?:and|with|versus|vs[.]?)\s+(.{1,120}?)[?.]?$",
            re.I,
        ),
        re.compile(
            r"\bdifferences?\s+between\s+(.{1,120}?)\s+and\s+(.{1,120}?)[?.]?$",
            re.I,
        ),
        re.compile(r"^(.{1,120}?)\s+(?:versus|vs[.]?)\s+(.{1,120}?)[?.]?$", re.I),
    )
    for pattern in patterns:
        match = pattern.search(query)
        if match:
            return [match.group(1), match.group(2)]
    return []


def _path_endpoints(query: str) -> list[str]:
    patterns = (
        re.compile(r"\bfrom\s+(.{1,120}?)\s+to\s+(.{1,120}?)[?.]?$", re.I),
        re.compile(r"\bbetween\s+(.{1,120}?)\s+and\s+(.{1,120}?)[?.]?$", re.I),
    )
    for pattern in patterns:
        match = pattern.search(query)
        if match:
            return [match.group(1), match.group(2)]
    return []


def _matches_any(query: str, patterns: tuple[re.Pattern, ...]) -> bool:
    return any(pattern.search(query) for pattern in patterns)