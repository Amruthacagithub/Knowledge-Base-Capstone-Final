"""Add document lifecycle state and ingestion job ledger."""
from alembic import op
import sqlalchemy as sa


revision = "0003_document_lifecycle_jobs"
down_revision = "0002_document_versions_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_kind",
                sa.String(),
                server_default="manifest",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("deprecated_at", sa.DateTime(), nullable=True))
        batch_op.create_check_constraint(
            "ck_document_source_kind",
            "source_kind IN ('manifest', 'upload')",
        )
        batch_op.create_index(
            "ix_documents_source_active",
            ["source_kind", "is_active"],
        )

    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("document_version_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunks_processed", sa.Integer(), nullable=False),
        sa.Column("vectors_upserted", sa.Integer(), nullable=False),
        sa.Column("bm25_indexed", sa.Integer(), nullable=False),
        sa.Column("triggered_by_user_id", sa.String(), nullable=True),
        sa.CheckConstraint("bm25_indexed >= 0", name="ck_ingest_job_bm25"),
        sa.CheckConstraint("chunks_processed >= 0", name="ck_ingest_job_chunks"),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_ingest_job_status",
        ),
        sa.CheckConstraint("vectors_upserted >= 0", name="ck_ingest_job_vectors"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingest_jobs_status_started",
        "ingest_jobs",
        ["status", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_jobs_status_started", table_name="ingest_jobs")
    op.drop_table("ingest_jobs")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_source_active")
        batch_op.drop_constraint("ck_document_source_kind", type_="check")
        batch_op.drop_column("deprecated_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("source_kind")