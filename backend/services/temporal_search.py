"""Permission-safe retrieval over immutable relational document history."""
import calendar
import re
from collections import defaultdict
from datetime import datetime, timezone

from backend.models import Chunk, Document, DocumentVersion
from backend.services.auth import UserContext
from backend.services.evidence_access import apply_document_access
from backend.services.query_router import TemporalIntent, classify_temporal_intent


MAX_TEMPORAL_CANDIDATES = 12
_TEMPORAL_STOP_WORDS = {
    "as",
    "at",
    "before",
    "changed",
    "current",
    "did",
    "effective",
    "has",
    "historical",
    "in",
    "latest",
    "of",
    "policy",
    "previous",
    "rules",
    "the",
    "today",
    "version",
    "versions",
    "was",
    "what",
}
_MONTHS = {
    month.casefold(): index
    for index, month in enumerate(calendar.month_name)
    if month
}


def retrieve_temporal_candidates(
    db,
    user_ctx: UserContext,
    query: str,
    *,
    limit: int = MAX_TEMPORAL_CANDIDATES,
) -> list[dict]:
    """Retrieve selected visible versions without querying current-only projections."""
    intent = classify_temporal_intent(query)
    if intent == "none":
        return []
    rows = _visible_chunk_rows(db, user_ctx)
    grouped = _group_rows(rows)
    effective_at = _parse_effective_at(query)
    query_tokens = _content_tokens(query)
    candidates = []
    for document_id, item in grouped.items():
        selected_versions = _select_versions(
            list(item["versions"].values()),
            intent,
            effective_at,
        )
        if not selected_versions:
            continue
        per_version_limit = max(1, limit // len(selected_versions))
        for version in selected_versions:
            chunks = item["chunks"].get(str(version.id), [])
            ranked_chunks = _rank_chunks(item["document"], version, chunks, query_tokens)
            for score, chunk in ranked_chunks[:per_version_limit]:
                candidates.append(
                    _candidate(item["document"], version, chunk, intent, score)
                )
    candidates.sort(
        key=lambda candidate: (
            -candidate["score"],
            candidate["doc_id"],
            candidate["version_number"],
            candidate["chunk_id"],
        )
    )
    return candidates[:limit]


def _visible_chunk_rows(db, user_ctx: UserContext):
    query = (
        db.query(Document, DocumentVersion, Chunk)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(Chunk, Chunk.document_version_id == DocumentVersion.id)
        .filter(Document.is_active.is_(True))
    )
    return apply_document_access(query, user_ctx).all()


def _group_rows(rows):
    grouped = {}
    for document, version, chunk in rows:
        item = grouped.setdefault(
            str(document.id),
            {
                "document": document,
                "versions": {},
                "chunks": defaultdict(list),
            },
        )
        item["versions"][str(version.id)] = version
        item["chunks"][str(version.id)].append(chunk)
    return grouped


def _select_versions(
    versions: list[DocumentVersion],
    intent: TemporalIntent,
    effective_at: datetime | None,
) -> list[DocumentVersion]:
    if intent == "change":
        ordered = sorted(versions, key=lambda version: version.version_number)
        return ordered[-2:]
    if intent == "historical":
        if effective_at is not None:
            effective = [
                version for version in versions if _is_effective(version, effective_at)
            ]
            return _highest_authority(effective)
        previous = [version for version in versions if not version.is_current]
        return _highest_authority(previous)
    current = [version for version in versions if version.is_current]
    return _highest_authority(current)


def _highest_authority(versions: list[DocumentVersion]) -> list[DocumentVersion]:
    if not versions:
        return []
    selected = max(
        versions,
        key=lambda version: (version.authority_level, version.version_number),
    )
    return [selected]


def _is_effective(version: DocumentVersion, effective_at: datetime) -> bool:
    start = _aware(version.effective_from)
    end = _aware(version.effective_to)
    return (start is None or start <= effective_at) and (
        end is None or effective_at < end
    )


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _rank_chunks(document, version, chunks, query_tokens):
    ranked = []
    for chunk in chunks:
        evidence_tokens = _tokens(f"{document.title} {chunk.text_content}")
        overlap = len(query_tokens & evidence_tokens) / max(len(query_tokens), 1)
        if query_tokens and overlap == 0:
            continue
        authority = float(version.authority_level) / 100.0
        ranked.append((0.8 * overlap + 0.2 * authority, chunk))
    return sorted(ranked, key=lambda item: (-item[0], item[1].sequence_index))


def _candidate(document, version, chunk, intent, score) -> dict:
    return {
        "chunk_id": str(chunk.id),
        "doc_id": str(document.id),
        "document_version_id": str(version.id),
        "version_number": int(version.version_number),
        "doc_title": str(document.title),
        "department": str(document.department),
        "text": str(chunk.text_content),
        "file_type": str(version.file_type),
        "page_start": int(chunk.page_start),
        "page_end": int(chunk.page_end),
        "score": float(score),
        "temporal_intent": intent,
    }


def _parse_effective_at(query: str) -> datetime | None:
    iso_match = re.search(r"\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b", query)
    if iso_match:
        year, month, day = (int(value) for value in iso_match.groups())
        try:
            return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
        except ValueError:
            return None
    month_match = re.search(
        r"\b(" + "|".join(_MONTHS) + r")\s+((?:19|20)\d{2})\b",
        query,
        re.I,
    )
    if month_match:
        month = _MONTHS[month_match.group(1).casefold()]
        year = int(month_match.group(2))
        day = calendar.monthrange(year, month)[1]
        return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
    year_match = re.search(r"\b((?:19|20)\d{2})\b", query)
    if year_match:
        return datetime(int(year_match.group(1)), 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    return None


def _content_tokens(value: str) -> set[str]:
    return _tokens(value) - _TEMPORAL_STOP_WORDS


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1
    }