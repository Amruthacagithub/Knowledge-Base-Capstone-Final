"""Add ID-only graph retrieval traces."""
from alembic import op
import sqlalchemy as sa


revision = "0005_retrieval_traces"
down_revision = "0004_evidence_graph_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retrieval_traces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("route", sa.String(), nullable=False),
        sa.Column("start_entity_id", sa.String(), nullable=True),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("max_paths", sa.Integer(), nullable=False),
        sa.Column("returned_paths", sa.Integer(), nullable=False),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("weights_json", sa.JSON(), nullable=False),
        sa.Column("paths_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "max_depth >= 1 AND max_depth <= 3",
            name="ck_retrieval_trace_depth",
        ),
        sa.CheckConstraint(
            "max_paths >= 1 AND max_paths <= 100",
            name="ck_retrieval_trace_paths",
        ),
        sa.CheckConstraint(
            "returned_paths >= 0",
            name="ck_retrieval_trace_returned",
        ),
        sa.ForeignKeyConstraint(
            ["start_entity_id"],
            ["entities.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_retrieval_traces_user_created",
        "retrieval_traces",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_traces_user_created",
        table_name="retrieval_traces",
    )
    op.drop_table("retrieval_traces")