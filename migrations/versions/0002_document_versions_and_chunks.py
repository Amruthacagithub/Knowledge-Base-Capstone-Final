"""Add immutable document versions and canonical chunks."""
from alembic import op
import sqlalchemy as sa


revision = "0002_document_versions_chunks"
down_revision = "0001_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("authority_level", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("superseded_by_id", sa.String(), nullable=True),
        sa.CheckConstraint(
            "authority_level >= 0 AND authority_level <= 100",
            name="ck_document_version_authority",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_document_version_effective_range",
        ),
        sa.CheckConstraint("version_number > 0", name="ck_document_version_positive"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["document_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "content_hash",
            name="uq_document_version_content",
        ),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_version_number",
        ),
    )
    op.create_index(
        "ix_document_versions_current",
        "document_versions",
        ["document_id", "is_current"],
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_version_id", sa.String(), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("section_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("page_end >= page_start", name="ck_chunk_page_range"),
        sa.CheckConstraint("page_start > 0", name="ck_chunk_page_start_positive"),
        sa.CheckConstraint("sequence_index >= 0", name="ck_chunk_sequence_nonnegative"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "sequence_index",
            name="uq_chunk_version_sequence",
        ),
    )
    op.create_index(
        "ix_chunks_document_version",
        "chunks",
        ["document_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_document_version", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_document_versions_current", table_name="document_versions")
    op.drop_table("document_versions")