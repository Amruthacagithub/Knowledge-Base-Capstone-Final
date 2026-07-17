"""Bounded authorization-first traversal over the evidence graph."""
import re
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EvidenceRelationship,
    RetrievalTrace,
)
from backend.services.auth import UserContext
from backend.services.audit import query_fingerprint
from backend.services.evidence_access import apply_document_access, is_entity_visible


MAX_TRAVERSAL_DEPTH = 3
MAX_TRAVERSAL_PATHS = 100


class GraphEntityUnavailable(LookupError):
    """Raised when a start entity does not exist or is not visible."""


@dataclass(frozen=True)
class TraversalEdge:
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    chunk_id: str
    document_id: str
    document_version_id: str
    document_title: str
    department: str
    source_entity_name: str
    target_entity_name: str
    evidence_text: str
    confidence: float
    authority_level: int
    effective_from: datetime | None


@dataclass(frozen=True)
class EvidencePath:
    entity_ids: tuple[str, ...]
    edges: tuple[TraversalEdge, ...]


@dataclass(frozen=True)
class TraversalResult:
    start_entity_id: str
    paths: tuple[EvidencePath, ...]
    truncated: bool


@dataclass(frozen=True)
class PathScore:
    relevance: float
    coherence: float
    authority: float
    freshness: float
    conflict_penalty: float
    total: float


@dataclass(frozen=True)
class RankedEvidencePath:
    path: EvidencePath
    score: PathScore


@dataclass(frozen=True)
class TracedTraversalResult:
    traversal: TraversalResult
    ranked_paths: tuple[RankedEvidencePath, ...]
    trace_id: str


@dataclass(frozen=True)
class PathScoreWeights:
    relevance: float = 0.40
    coherence: float = 0.20
    authority: float = 0.20
    freshness: float = 0.10
    conflict_penalty: float = 0.10


def traverse_visible_graph(
    db,
    user_ctx: UserContext,
    start_entity_id: str,
    *,
    max_depth: int = 2,
    max_paths: int = 50,
) -> TraversalResult:
    """Traverse outgoing edges without exposing inaccessible graph structure."""
    _validate_limits(max_depth, max_paths)
    if not is_entity_visible(db, start_entity_id, user_ctx):
        raise GraphEntityUnavailable("Entity not found")

    frontier = [EvidencePath(entity_ids=(start_entity_id,), edges=())]
    discovered: list[EvidencePath] = []
    truncated = False

    for _depth in range(max_depth):
        if not frontier:
            break
        source_ids = {path.entity_ids[-1] for path in frontier}
        edges_by_source = _visible_edges_by_source(db, user_ctx, source_ids)
        next_frontier, truncated = _expand_frontier(
            frontier,
            edges_by_source,
            discovered,
            max_paths,
        )
        if truncated:
            break
        frontier = next_frontier

    return TraversalResult(
        start_entity_id=start_entity_id,
        paths=tuple(discovered),
        truncated=truncated,
    )


def _expand_frontier(
    frontier: list[EvidencePath],
    edges_by_source: dict[str, list[TraversalEdge]],
    discovered: list[EvidencePath],
    max_paths: int,
) -> tuple[list[EvidencePath], bool]:
    next_frontier = []
    for path in frontier:
        source_id = path.entity_ids[-1]
        for edge in edges_by_source.get(source_id, ()):
            if edge.target_entity_id in path.entity_ids:
                continue
            extended = EvidencePath(
                entity_ids=(*path.entity_ids, edge.target_entity_id),
                edges=(*path.edges, edge),
            )
            discovered.append(extended)
            next_frontier.append(extended)
            if len(discovered) >= max_paths:
                return next_frontier, True
    return next_frontier, False


def rank_evidence_paths(
    paths: tuple[EvidencePath, ...],
    query: str,
    *,
    conflicting_relationship_ids: set[str] | None = None,
    now: datetime | None = None,
    weights: PathScoreWeights = PathScoreWeights(),
) -> tuple[RankedEvidencePath, ...]:
    """Rank authorized paths with inspectable normalized score components."""
    _validate_weights(weights)
    conflict_ids = conflicting_relationship_ids or set()
    current_time = now or datetime.now(timezone.utc)
    ranked = [
        RankedEvidencePath(
            path=path,
            score=_score_path(path, query, conflict_ids, current_time, weights),
        )
        for path in paths
    ]
    return tuple(
        sorted(
            ranked,
            key=lambda ranked_path: (
                -ranked_path.score.total,
                ranked_path.path.entity_ids,
            ),
        )
    )


def traverse_rank_and_trace(
    db,
    user_ctx: UserContext,
    start_entity_id: str,
    query: str,
    *,
    max_depth: int = 2,
    max_paths: int = 50,
    conflicting_relationship_ids: set[str] | None = None,
    now: datetime | None = None,
    weights: PathScoreWeights = PathScoreWeights(),
) -> TracedTraversalResult:
    """Traverse, rank, and stage an ID-only audit trace in the caller transaction."""
    traversal = traverse_visible_graph(
        db,
        user_ctx,
        start_entity_id,
        max_depth=max_depth,
        max_paths=max_paths,
    )
    ranked_paths = rank_evidence_paths(
        traversal.paths,
        query,
        conflicting_relationship_ids=conflicting_relationship_ids,
        now=now,
        weights=weights,
    )
    trace_id = str(uuid.uuid4())
    db.add(
        RetrievalTrace(
            id=trace_id,
            user_id=user_ctx.user_id,
            query_text=f"sha256:{query_fingerprint(query)}",
            route="graph",
            start_entity_id=start_entity_id,
            max_depth=max_depth,
            max_paths=max_paths,
            returned_paths=len(ranked_paths),
            truncated=traversal.truncated,
            weights_json=asdict(weights),
            paths_json=[_trace_path(item) for item in ranked_paths],
        )
    )
    db.flush()
    return TracedTraversalResult(
        traversal=traversal,
        ranked_paths=ranked_paths,
        trace_id=trace_id,
    )


def _visible_edges_by_source(db, user_ctx, source_ids: set[str]):
    if not source_ids:
        return {}
    entity_names = {
        str(entity.id): str(entity.display_name)
        for entity in db.query(Entity).filter(Entity.id.in_(source_ids)).all()
    }
    rows = (
        db.query(EvidenceRelationship, Chunk, DocumentVersion, Document)
        .join(Chunk, Chunk.id == EvidenceRelationship.chunk_id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .filter(
            EvidenceRelationship.source_entity_id.in_(source_ids),
            Document.is_active.is_(True),
            DocumentVersion.is_current.is_(True),
        )
    )
    rows = apply_document_access(rows, user_ctx).order_by(EvidenceRelationship.id).all()
    target_ids = {
        str(relationship.target_entity_id)
        for relationship, _chunk, _version, _document in rows
    }
    entity_names.update(
        {
            str(entity.id): str(entity.display_name)
            for entity in db.query(Entity).filter(Entity.id.in_(target_ids)).all()
        }
    )
    grouped: dict[str, list[TraversalEdge]] = {}
    for relationship, chunk, version, document in rows:
        edge = TraversalEdge(
            relationship_id=str(relationship.id),
            source_entity_id=str(relationship.source_entity_id),
            target_entity_id=str(relationship.target_entity_id),
            relationship_type=str(relationship.relationship_type),
            chunk_id=str(chunk.id),
            document_id=str(document.id),
            document_version_id=str(version.id),
            document_title=str(document.title),
            department=str(document.department),
            source_entity_name=entity_names[str(relationship.source_entity_id)],
            target_entity_name=entity_names[str(relationship.target_entity_id)],
            evidence_text=str(relationship.evidence_text),
            confidence=float(relationship.confidence),
            authority_level=int(version.authority_level),
            effective_from=version.effective_from,
        )
        grouped.setdefault(edge.source_entity_id, []).append(edge)
    return grouped


def _validate_limits(max_depth: int, max_paths: int) -> None:
    if not 1 <= max_depth <= MAX_TRAVERSAL_DEPTH:
        raise ValueError(f"max_depth must be between 1 and {MAX_TRAVERSAL_DEPTH}")
    if not 1 <= max_paths <= MAX_TRAVERSAL_PATHS:
        raise ValueError(f"max_paths must be between 1 and {MAX_TRAVERSAL_PATHS}")


def _score_path(path, query, conflict_ids, now, weights) -> PathScore:
    edge_count = len(path.edges)
    path_text = " ".join(
        f"{edge.source_entity_name} {edge.relationship_type} "
        f"{edge.target_entity_name}"
        for edge in path.edges
    )
    relevance = _token_overlap(query, path_text)
    coherence = sum(edge.confidence for edge in path.edges) / edge_count
    authority = sum(edge.authority_level / 100 for edge in path.edges) / edge_count
    freshness = sum(_freshness(edge.effective_from, now) for edge in path.edges) / edge_count
    conflict_penalty = (
        sum(edge.relationship_id in conflict_ids for edge in path.edges) / edge_count
    )
    total = (
        weights.relevance * relevance
        + weights.coherence * coherence
        + weights.authority * authority
        + weights.freshness * freshness
        - weights.conflict_penalty * conflict_penalty
    )
    return PathScore(
        relevance=relevance,
        coherence=coherence,
        authority=authority,
        freshness=freshness,
        conflict_penalty=conflict_penalty,
        total=total,
    )


def _token_overlap(query: str, path_text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(path_text)) / len(query_tokens)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1
    }


def _freshness(effective_from: datetime | None, now: datetime) -> float:
    if effective_from is None:
        return 0.5
    timestamp = effective_from
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_days = max((now - timestamp).total_seconds() / 86400, 0.0)
    return 1.0 / (1.0 + age_days / 365.0)


def _validate_weights(weights: PathScoreWeights) -> None:
    values = (
        weights.relevance,
        weights.coherence,
        weights.authority,
        weights.freshness,
        weights.conflict_penalty,
    )
    if any(value < 0 for value in values):
        raise ValueError("path score weights must be non-negative")
    if abs(sum(values) - 1.0) > 1e-9:
        raise ValueError("path score weights must sum to 1.0")


def _trace_path(ranked_path: RankedEvidencePath) -> dict:
    return {
        "entity_ids": list(ranked_path.path.entity_ids),
        "relationship_ids": [
            edge.relationship_id for edge in ranked_path.path.edges
        ],
        "chunk_ids": [edge.chunk_id for edge in ranked_path.path.edges],
        "document_ids": [edge.document_id for edge in ranked_path.path.edges],
        "score": asdict(ranked_path.score),
    }