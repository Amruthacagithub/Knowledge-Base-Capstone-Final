"""
SQLAlchemy ORM models for EKIP.
Tables: users, roles, user_roles, documents, access_audit_log.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON,
    Table, UniqueConstraint, CheckConstraint, Index, true
)
from sqlalchemy.orm import relationship
from backend.database import Base


DOCUMENT_VERSION_REFERENCE = "document_versions.id"
DOCUMENT_REFERENCE = "documents.id"
ON_DELETE_SET_NULL = "SET NULL"
ENTITY_REFERENCE = "entities.id"
CHUNK_REFERENCE = "chunks.id"
EXTRACTION_RUN_REFERENCE = "extraction_runs.id"
CONFIDENCE_CHECK = "confidence >= 0 AND confidence <= 1"


# ── Association table: user <-> role (many-to-many) ──
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.user_id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.role_id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    department = Column(String, nullable=False)
    password_hash = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    roles = relationship("Role", secondary=user_roles, back_populates="users")

    def role_names(self):
        return [r.role_name for r in self.roles]


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary=user_roles, back_populates="roles")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_expires", "user_id", "expires_at"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('manifest', 'upload')",
            name="ck_document_source_kind",
        ),
        Index("ix_documents_source_active", "source_kind", "is_active"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(Text, nullable=False)
    department = Column(String, nullable=False)
    classification = Column(String, nullable=False)  # "public" or "restricted"
    file_path = Column(Text, nullable=False)
    source_kind = Column(String, nullable=False, default="manifest")
    is_active = Column(Boolean, nullable=False, default=True)
    deprecated_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id",
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
        UniqueConstraint("document_id", "content_hash", name="uq_document_version_content"),
        CheckConstraint("version_number > 0", name="ck_document_version_positive"),
        CheckConstraint(
            "authority_level >= 0 AND authority_level <= 100",
            name="ck_document_version_authority",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_document_version_effective_range",
        ),
        Index("ix_document_versions_current", "document_id", "is_current"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String,
        ForeignKey(DOCUMENT_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False)
    storage_uri = Column(Text, nullable=False)
    file_type = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    uploaded_by_user_id = Column(String)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    authority_level = Column(Integer, nullable=False, default=50)
    is_current = Column(Boolean, nullable=False, default=True)
    superseded_by_id = Column(
        String,
        ForeignKey(DOCUMENT_VERSION_REFERENCE, ondelete=ON_DELETE_SET_NULL),
    )

    document = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )
    chunks = relationship(
        "Chunk",
        back_populates="document_version",
        cascade="all, delete-orphan",
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "sequence_index",
            name="uq_chunk_version_sequence",
        ),
        CheckConstraint("sequence_index >= 0", name="ck_chunk_sequence_nonnegative"),
        CheckConstraint("page_start > 0", name="ck_chunk_page_start_positive"),
        CheckConstraint("page_end >= page_start", name="ck_chunk_page_range"),
        Index("ix_chunks_document_version", "document_version_id"),
    )

    id = Column(String, primary_key=True)
    document_version_id = Column(
        String,
        ForeignKey(DOCUMENT_VERSION_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    sequence_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    page_start = Column(Integer, nullable=False, default=1)
    page_end = Column(Integer, nullable=False, default=1)
    section_path = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document_version = relationship("DocumentVersion", back_populates="chunks")


class IngestJob(Base):
    __tablename__ = "ingest_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_ingest_job_status",
        ),
        CheckConstraint("chunks_processed >= 0", name="ck_ingest_job_chunks"),
        CheckConstraint("vectors_upserted >= 0", name="ck_ingest_job_vectors"),
        CheckConstraint("bm25_indexed >= 0", name="ck_ingest_job_bm25"),
        Index("ix_ingest_jobs_status_started", "status", "started_at"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_path = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    source_kind = Column(String, nullable=False, default="manifest")
    status = Column(String, nullable=False, default="running")
    document_id = Column(
        String,
        ForeignKey(DOCUMENT_REFERENCE, ondelete=ON_DELETE_SET_NULL),
    )
    document_version_id = Column(
        String,
        ForeignKey(DOCUMENT_VERSION_REFERENCE, ondelete=ON_DELETE_SET_NULL),
    )
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    chunks_processed = Column(Integer, nullable=False, default=0)
    vectors_upserted = Column(Integer, nullable=False, default=0)
    bm25_indexed = Column(Integer, nullable=False, default=0)
    triggered_by_user_id = Column(String)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_extraction_run_status",
        ),
        UniqueConstraint(
            "document_version_id",
            "extractor_name",
            "extractor_version",
            "schema_version",
            name="uq_extraction_run_version",
        ),
        Index("ix_extraction_runs_status_started", "status", "started_at"),
    )

    id = Column(String, primary_key=True)
    document_version_id = Column(
        String,
        ForeignKey(DOCUMENT_VERSION_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    extractor_name = Column(String, nullable=False)
    extractor_version = Column(String, nullable=False)
    schema_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="running")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime)
    error_message = Column(Text)


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("entity_type", "canonical_name", name="uq_entity_identity"),
        Index("ix_entities_type_name", "entity_type", "canonical_name"),
    )

    id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False)
    canonical_name = Column(String, nullable=False)
    display_name = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class EntityMention(Base):
    __tablename__ = "entity_mentions"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "entity_id",
            "start_char",
            "end_char",
            name="uq_entity_mention_span",
        ),
        CheckConstraint("start_char >= 0", name="ck_entity_mention_start"),
        CheckConstraint("end_char > start_char", name="ck_entity_mention_range"),
        CheckConstraint(
            CONFIDENCE_CHECK,
            name="ck_entity_mention_confidence",
        ),
        Index("ix_entity_mentions_chunk", "chunk_id"),
        Index("ix_entity_mentions_entity", "entity_id"),
    )

    id = Column(String, primary_key=True)
    entity_id = Column(
        String,
        ForeignKey(ENTITY_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id = Column(
        String,
        ForeignKey(CHUNK_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    extraction_run_id = Column(
        String,
        ForeignKey(EXTRACTION_RUN_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    surface_text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)


class EvidenceClaim(Base):
    __tablename__ = "evidence_claims"
    __table_args__ = (
        UniqueConstraint("chunk_id", "claim_hash", name="uq_evidence_claim_chunk_hash"),
        CheckConstraint(
            CONFIDENCE_CHECK,
            name="ck_evidence_claim_confidence",
        ),
        Index("ix_evidence_claims_chunk", "chunk_id"),
        Index("ix_evidence_claims_subject", "subject_entity_id"),
    )

    id = Column(String, primary_key=True)
    chunk_id = Column(
        String,
        ForeignKey(CHUNK_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    extraction_run_id = Column(
        String,
        ForeignKey(EXTRACTION_RUN_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    subject_entity_id = Column(
        String,
        ForeignKey(ENTITY_REFERENCE, ondelete=ON_DELETE_SET_NULL),
    )
    claim_hash = Column(String(64), nullable=False)
    claim_text = Column(Text, nullable=False)
    predicate = Column(String)
    object_text = Column(Text)
    polarity = Column(Boolean, nullable=False, default=True)
    confidence = Column(Float, nullable=False, default=1.0)
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)


class EvidenceRelationship(Base):
    __tablename__ = "evidence_relationships"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_evidence_relationship",
        ),
        CheckConstraint(
            "source_entity_id <> target_entity_id",
            name="ck_evidence_relationship_distinct",
        ),
        CheckConstraint(
            CONFIDENCE_CHECK,
            name="ck_evidence_relationship_confidence",
        ),
        Index("ix_evidence_relationships_source", "source_entity_id"),
        Index("ix_evidence_relationships_target", "target_entity_id"),
        Index("ix_evidence_relationships_chunk", "chunk_id"),
    )

    id = Column(String, primary_key=True)
    chunk_id = Column(
        String,
        ForeignKey(CHUNK_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    extraction_run_id = Column(
        String,
        ForeignKey(EXTRACTION_RUN_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    source_entity_id = Column(
        String,
        ForeignKey(ENTITY_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    target_entity_id = Column(
        String,
        ForeignKey(ENTITY_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type = Column(String, nullable=False)
    evidence_text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)


class RetrievalTrace(Base):
    __tablename__ = "retrieval_traces"
    __table_args__ = (
        CheckConstraint(
            "max_depth >= 1 AND max_depth <= 3",
            name="ck_retrieval_trace_depth",
        ),
        CheckConstraint(
            "max_paths >= 1 AND max_paths <= 100",
            name="ck_retrieval_trace_paths",
        ),
        CheckConstraint("returned_paths >= 0", name="ck_retrieval_trace_returned"),
        Index("ix_retrieval_traces_user_created", "user_id", "created_at"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    query_text = Column(Text, nullable=False)
    route = Column(String, nullable=False, default="graph")
    start_entity_id = Column(
        String,
        ForeignKey(ENTITY_REFERENCE, ondelete=ON_DELETE_SET_NULL),
    )
    max_depth = Column(Integer, nullable=False)
    max_paths = Column(Integer, nullable=False)
    returned_paths = Column(Integer, nullable=False)
    truncated = Column(Boolean, nullable=False, default=False)
    weights_json = Column(JSON, nullable=False)
    paths_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class QueryExecutionTrace(Base):
    __tablename__ = "query_execution_traces"
    __table_args__ = (
        CheckConstraint(
            "route IN ('local', 'global', 'multi_hop', 'temporal', 'comparison')",
            name="ck_query_execution_trace_route",
        ),
        CheckConstraint("query_length >= 0", name="ck_query_execution_trace_length"),
        CheckConstraint("subquery_count >= 0", name="ck_query_execution_trace_subqueries"),
        Index("ix_query_execution_traces_user_created", "user_id", "created_at"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    query_hash = Column(String(64), nullable=False)
    query_length = Column(Integer, nullable=False)
    route = Column(String, nullable=False)
    subquery_count = Column(Integer, nullable=False, default=0)
    candidate_ids_json = Column(JSON, nullable=False)
    graph_trace_ids_json = Column(JSON, nullable=False)
    timings_json = Column(JSON, nullable=False)
    verification_json = Column(JSON, nullable=False)
    corrective_retrieval_used = Column(Boolean, nullable=False, default=False)
    authorization_applied = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ClaimConflict(Base):
    __tablename__ = "claim_conflicts"
    __table_args__ = (
        UniqueConstraint(
            "claim_a_id",
            "claim_b_id",
            "conflict_type",
            name="uq_claim_conflict_pair_type",
        ),
        CheckConstraint("claim_a_id < claim_b_id", name="ck_claim_conflict_order"),
        CheckConstraint(
            "status IN ('candidate', 'confirmed', 'dismissed')",
            name="ck_claim_conflict_status",
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_claim_conflict_confidence"),
        Index("ix_claim_conflicts_status_created", "status", "created_at"),
    )

    id = Column(String, primary_key=True)
    document_id = Column(
        String,
        ForeignKey(DOCUMENT_REFERENCE, ondelete="CASCADE"),
        nullable=False,
    )
    claim_a_id = Column(
        String,
        ForeignKey("evidence_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_b_id = Column(
        String,
        ForeignKey("evidence_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    conflict_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="candidate")
    confidence = Column(Float, nullable=False)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime)
    reviewed_by_user_id = Column(String)


class AccessAuditLog(Base):
    __tablename__ = "access_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    query_text = Column(Text)
    doc_ids = Column(Text)  # stored as comma-separated UUIDs for portability
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    allowed = Column(Boolean, nullable=False, default=True)
