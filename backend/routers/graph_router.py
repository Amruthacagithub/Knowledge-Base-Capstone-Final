"""Permission-safe evidence graph API."""
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from backend.config import EVIDENCE_GRAPH_ENABLED
from backend.database import SessionLocal
from backend.services.auth import UserContext, authenticate
from backend.services.evidence_access import visible_entities
from backend.services.graph_traversal import (
    GraphEntityUnavailable,
    RankedEvidencePath,
    traverse_rank_and_trace,
)


router = APIRouter(prefix="/api/graph", tags=["evidence-graph"])


class EntitySummary(BaseModel):
    id: str
    entity_type: str
    canonical_name: str
    display_name: str


class ScoreItem(BaseModel):
    relevance: float
    coherence: float
    authority: float
    freshness: float
    conflict_penalty: float
    total: float


class EdgeItem(BaseModel):
    relationship_id: str
    source_entity_id: str
    source_entity_name: str
    target_entity_id: str
    target_entity_name: str
    relationship_type: str
    chunk_id: str
    document_id: str
    document_version_id: str
    document_title: str
    department: str
    evidence_text: str
    confidence: float


class PathItem(BaseModel):
    entity_ids: list[str]
    edges: list[EdgeItem]
    score: ScoreItem


class GraphPathsResponse(BaseModel):
    trace_id: str
    start_entity_id: str
    truncated: bool
    paths: list[PathItem]


@router.get(
    "/entities",
    response_model=list[EntitySummary],
    responses={401: {"description": "Invalid or expired token"}, 404: {"description": "Graph disabled"}},
)
def list_graph_entities(
    authorization: Annotated[str, Header()],
    query: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    """List visible matching entities without exposing hidden corpus counts."""
    _require_graph_enabled()
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        needle = query.strip().lower()
        matches = [
            entity
            for entity in visible_entities(db, user_ctx)
            if needle in str(entity.canonical_name).lower()
            or needle in str(entity.display_name).lower()
        ][:limit]
        return [
            EntitySummary(
                id=str(entity.id),
                entity_type=str(entity.entity_type),
                canonical_name=str(entity.canonical_name),
                display_name=str(entity.display_name),
            )
            for entity in matches
        ]
    finally:
        db.close()


@router.get(
    "/entities/{entity_id}/paths",
    response_model=GraphPathsResponse,
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Graph disabled, entity hidden, or entity missing"},
    },
)
def get_graph_paths(
    entity_id: str,
    authorization: Annotated[str, Header()],
    query: Annotated[str, Query(min_length=1, max_length=500)],
    depth: Annotated[int, Query(ge=1, le=3)] = 2,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """Return ranked authorized evidence paths and persist an ID-only trace."""
    _require_graph_enabled()
    user_ctx = _require_user(authorization)
    db = SessionLocal()
    try:
        try:
            result = traverse_rank_and_trace(
                db,
                user_ctx,
                entity_id,
                query,
                max_depth=depth,
                max_paths=limit,
            )
        except GraphEntityUnavailable as exc:
            raise HTTPException(status_code=404, detail="Entity not found") from exc
        db.commit()
        return GraphPathsResponse(
            trace_id=result.trace_id,
            start_entity_id=result.traversal.start_entity_id,
            truncated=result.traversal.truncated,
            paths=[_path_item(path) for path in result.ranked_paths],
        )
    finally:
        db.close()


def _path_item(ranked_path: RankedEvidencePath) -> PathItem:
    return PathItem(
        entity_ids=list(ranked_path.path.entity_ids),
        edges=[EdgeItem(**edge.__dict__) for edge in ranked_path.path.edges],
        score=ScoreItem(**ranked_path.score.__dict__),
    )


def _require_graph_enabled() -> None:
    if not EVIDENCE_GRAPH_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


def _require_user(authorization: str) -> UserContext:
    token = authorization.removeprefix("Bearer ").strip()
    user_ctx = authenticate(token)
    if user_ctx is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_ctx