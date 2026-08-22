"""Add provenance-first evidence graph tables."""
from alembic import op
import sqlalchemy as sa


revision = "0004_evidence_graph_schema"
down_revision = "0003_document_lifecycle_jobs"
branch_labels = None
depends_on = None

CONFIDENCE_CHECK = "confidence >= 0 AND confidence <= 1"
CHUNK_REFERENCE = "chunks.id"
ENTITY_REFERENCE = "entities.id"
EXTRACTION_RUN_REFERENCE = "extraction_runs.id"


def upgrade() -> None:
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_version_id", sa.String(), nullable=False),
        sa.Column("extractor_name", sa.String(), nullable=False),
        sa.Column("extractor_version", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_extraction_run_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "extractor_name",
            "extractor_version",
            "schema_version",
            name="uq_extraction_run_version",
        ),
    )
    op.create_index(
        "ix_extraction_runs_status_started",
        "extraction_runs",
        ["status", "started_at"],
    )
    op.create_table(
        "entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "canonical_name", name="uq_entity_identity"),
    )
    op.create_index(
        "ix_entities_type_name",
        "entities",
        ["entity_type", "canonical_name"],
    )
    op.create_table(
        "entity_mentions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("extraction_run_id", sa.String(), nullable=False),
        sa.Column("surface_text", sa.Text(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_entity_mention_confidence"),
        sa.CheckConstraint("end_char > start_char", name="ck_entity_mention_range"),
        sa.CheckConstraint("start_char >= 0", name="ck_entity_mention_start"),
        sa.ForeignKeyConstraint(["chunk_id"], [CHUNK_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], [ENTITY_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_run_id"], [EXTRACTION_RUN_REFERENCE], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "entity_id", "start_char", "end_char", name="uq_entity_mention_span"),
    )
    op.create_index("ix_entity_mentions_chunk", "entity_mentions", ["chunk_id"])
    op.create_index("ix_entity_mentions_entity", "entity_mentions", ["entity_id"])
    op.create_table(
        "evidence_claims",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("extraction_run_id", sa.String(), nullable=False),
        sa.Column("subject_entity_id", sa.String(), nullable=True),
        sa.Column("claim_hash", sa.String(length=64), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("predicate", sa.String(), nullable=True),
        sa.Column("object_text", sa.Text(), nullable=True),
        sa.Column("polarity", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_evidence_claim_confidence"),
        sa.ForeignKeyConstraint(["chunk_id"], [CHUNK_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_run_id"], [EXTRACTION_RUN_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_entity_id"], [ENTITY_REFERENCE], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "claim_hash", name="uq_evidence_claim_chunk_hash"),
    )
    op.create_index("ix_evidence_claims_chunk", "evidence_claims", ["chunk_id"])
    op.create_index("ix_evidence_claims_subject", "evidence_claims", ["subject_entity_id"])
    op.create_table(
        "evidence_relationships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("extraction_run_id", sa.String(), nullable=False),
        sa.Column("source_entity_id", sa.String(), nullable=False),
        sa.Column("target_entity_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_evidence_relationship_confidence"),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_evidence_relationship_distinct"),
        sa.ForeignKeyConstraint(["chunk_id"], [CHUNK_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_run_id"], [EXTRACTION_RUN_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], [ENTITY_REFERENCE], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], [ENTITY_REFERENCE], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "source_entity_id", "target_entity_id", "relationship_type", name="uq_evidence_relationship"),
    )
    op.create_index("ix_evidence_relationships_chunk", "evidence_relationships", ["chunk_id"])
    op.create_index("ix_evidence_relationships_source", "evidence_relationships", ["source_entity_id"])
    op.create_index("ix_evidence_relationships_target", "evidence_relationships", ["target_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_relationships_target", table_name="evidence_relationships")
    op.drop_index("ix_evidence_relationships_source", table_name="evidence_relationships")
    op.drop_index("ix_evidence_relationships_chunk", table_name="evidence_relationships")
    op.drop_table("evidence_relationships")
    op.drop_index("ix_evidence_claims_subject", table_name="evidence_claims")
    op.drop_index("ix_evidence_claims_chunk", table_name="evidence_claims")
    op.drop_table("evidence_claims")
    op.drop_index("ix_entity_mentions_entity", table_name="entity_mentions")
    op.drop_index("ix_entity_mentions_chunk", table_name="entity_mentions")
    op.drop_table("entity_mentions")
    op.drop_index("ix_entities_type_name", table_name="entities")
    op.drop_table("entities")
    op.drop_index("ix_extraction_runs_status_started", table_name="extraction_runs")
    op.drop_table("extraction_runs")