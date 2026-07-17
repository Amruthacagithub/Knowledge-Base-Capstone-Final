"""Authorization-first access to extracted evidence graph artifacts."""
from sqlalchemy import and_, or_

from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EntityMention,
    EvidenceClaim,
    EvidenceRelationship,
)
from backend.services.auth import UserContext


_ROLE_DEPARTMENTS = {
    "HR": "HR",
    "Engineer": "Engineering",
    "Sales": "Sales",
}


def visible_entities(db, user_ctx: UserContext) -> list[Entity]:
    """Return only entities with at least one currently accessible mention."""
    query = (
        db.query(Entity)
        .join(EntityMention, EntityMention.entity_id == Entity.id)
        .join(Chunk, Chunk.id == EntityMention.chunk_id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .filter(Document.is_active.is_(True), DocumentVersion.is_current.is_(True))
    )
    query = apply_document_access(query, user_ctx)
    return query.distinct().order_by(Entity.entity_type, Entity.canonical_name).all()


def visible_claims(db, user_ctx: UserContext) -> list[EvidenceClaim]:
    """Return claims backed by currently accessible evidence chunks."""
    query = (
        db.query(EvidenceClaim)
        .join(Chunk, Chunk.id == EvidenceClaim.chunk_id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .filter(Document.is_active.is_(True), DocumentVersion.is_current.is_(True))
    )
    return apply_document_access(query, user_ctx).order_by(EvidenceClaim.id).all()


def visible_relationships(db, user_ctx: UserContext) -> list[EvidenceRelationship]:
    """Return graph edges backed by currently accessible evidence chunks."""
    query = (
        db.query(EvidenceRelationship)
        .join(Chunk, Chunk.id == EvidenceRelationship.chunk_id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .filter(Document.is_active.is_(True), DocumentVersion.is_current.is_(True))
    )
    return apply_document_access(query, user_ctx).order_by(
        EvidenceRelationship.id
    ).all()


def is_entity_visible(db, entity_id: str, user_ctx: UserContext) -> bool:
    """Return whether an entity has current evidence visible to this user."""
    query = (
        db.query(Entity.id)
        .join(EntityMention, EntityMention.entity_id == Entity.id)
        .join(Chunk, Chunk.id == EntityMention.chunk_id)
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .filter(
            Entity.id == entity_id,
            Document.is_active.is_(True),
            DocumentVersion.is_current.is_(True),
        )
    )
    return apply_document_access(query, user_ctx).first() is not None


def apply_document_access(query, user_ctx: UserContext):
    """Apply the central document visibility policy to an evidence query."""
    if "Admin" in user_ctx.roles:
        return query
    departments = {
        department
        for role, department in _ROLE_DEPARTMENTS.items()
        if role in user_ctx.roles
    }
    if not departments:
        return query.filter(Document.classification == "public")
    return query.filter(
        or_(
            Document.classification == "public",
            and_(
                Document.classification == "restricted",
                Document.department.in_(departments),
            ),
        )
    )