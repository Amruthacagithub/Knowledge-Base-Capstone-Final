"""Convert authorized evidence-graph paths into retrieval candidates."""
import re
from dataclasses import dataclass

from backend.services.auth import UserContext
from backend.services.evidence_access import visible_entities
from backend.services.graph_traversal import (
    GraphEntityUnavailable,
    traverse_rank_and_trace,
)


MAX_GRAPH_STARTS = 3
MAX_GRAPH_CANDIDATES = 12
_ENTITY_STOP_TOKENS = {"service", "system", "team", "policy", "the"}


@dataclass(frozen=True)
class GraphRetrievalResult:
    candidates: tuple[dict, ...]
    trace_ids: tuple[str, ...]


def retrieve_graph_candidates(
    db,
    user_ctx: UserContext,
    query: str,
    *,
    max_starts: int = MAX_GRAPH_STARTS,
    max_candidates: int = MAX_GRAPH_CANDIDATES,
) -> GraphRetrievalResult:
    """Traverse only query-matching entities already proven visible to the user."""
    starts = _matching_visible_entities(db, user_ctx, query)[:max_starts]
    traces = []
    candidates_by_chunk = {}
    for entity in starts:
        try:
            result = traverse_rank_and_trace(
                db,
                user_ctx,
                str(entity.id),
                query,
                max_depth=2,
                max_paths=50,
            )
        except GraphEntityUnavailable:
            continue
        traces.append(result.trace_id)
        _collect_path_candidates(candidates_by_chunk, result.ranked_paths)

    candidates = sorted(
        candidates_by_chunk.values(),
        key=lambda candidate: (-candidate["score"], candidate["chunk_id"]),
    )[:max_candidates]
    return GraphRetrievalResult(tuple(candidates), tuple(traces))


def _matching_visible_entities(db, user_ctx: UserContext, query: str):
    query_text = query.casefold()
    query_tokens = _tokens(query)
    ranked = []
    for entity in visible_entities(db, user_ctx):
        names = (
            str(entity.canonical_name).replace("_", " "),
            str(entity.display_name),
        )
        entity_tokens = set().union(*(_tokens(name) for name in names))
        meaningful = entity_tokens - _ENTITY_STOP_TOKENS
        overlap = len(query_tokens & meaningful)
        if overlap == 0:
            continue
        phrase_match = any(name.casefold() in query_text for name in names)
        ranked.append((int(phrase_match), overlap, str(entity.canonical_name), entity))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [item[3] for item in ranked]


def _collect_path_candidates(candidates_by_chunk: dict, ranked_paths) -> None:
    for ranked_path in ranked_paths:
        path_payload = _path_payload(ranked_path)
        for edge in ranked_path.path.edges:
            candidate = candidates_by_chunk.get(edge.chunk_id)
            if candidate is None:
                candidates_by_chunk[edge.chunk_id] = {
                    "chunk_id": edge.chunk_id,
                    "doc_id": edge.document_id,
                    "document_version_id": edge.document_version_id,
                    "doc_title": edge.document_title,
                    "department": edge.department,
                    "text": edge.evidence_text,
                    "file_type": "markdown",
                    "score": ranked_path.score.total,
                    "graph_relationship_ids": [edge.relationship_id],
                    "graph_entity_ids": list(ranked_path.path.entity_ids),
                    "graph_paths": [path_payload],
                }
                continue
            if edge.evidence_text not in candidate["text"]:
                candidate["text"] += f"\n{edge.evidence_text}"
            candidate["score"] = max(candidate["score"], ranked_path.score.total)
            if edge.relationship_id not in candidate["graph_relationship_ids"]:
                candidate["graph_relationship_ids"].append(edge.relationship_id)
            signatures = {
                tuple(path["relationship_ids"])
                for path in candidate["graph_paths"]
            }
            if tuple(path_payload["relationship_ids"]) not in signatures:
                candidate["graph_paths"].append(path_payload)


def _path_payload(ranked_path) -> dict:
    edges = ranked_path.path.edges
    entities = []
    if edges:
        entities.append(
            {"id": edges[0].source_entity_id, "name": edges[0].source_entity_name}
        )
        entities.extend(
            {"id": edge.target_entity_id, "name": edge.target_entity_name}
            for edge in edges
        )
    return {
        "entity_ids": list(ranked_path.path.entity_ids),
        "relationship_ids": [edge.relationship_id for edge in edges],
        "entities": entities,
        "relationships": [
            {
                "id": edge.relationship_id,
                "source_entity_id": edge.source_entity_id,
                "target_entity_id": edge.target_entity_id,
                "type": edge.relationship_type,
            }
            for edge in edges
        ],
        "score": float(ranked_path.score.total),
    }


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1
    }