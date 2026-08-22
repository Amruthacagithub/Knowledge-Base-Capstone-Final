"""Add privacy-preserving route-general query execution traces."""
from alembic import op
import sqlalchemy as sa


revision = "0007_query_execution_traces"
down_revision = "0006_claim_conflicts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_execution_traces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("query_length", sa.Integer(), nullable=False),
        sa.Column("route", sa.String(), nullable=False),
        sa.Column("subquery_count", sa.Integer(), nullable=False),
        sa.Column("candidate_ids_json", sa.JSON(), nullable=False),
        sa.Column("graph_trace_ids_json", sa.JSON(), nullable=False),
        sa.Column("timings_json", sa.JSON(), nullable=False),
        sa.Column("verification_json", sa.JSON(), nullable=False),
        sa.Column("corrective_retrieval_used", sa.Boolean(), nullable=False),
        sa.Column("authorization_applied", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "query_length >= 0",
            name="ck_query_execution_trace_length",
        ),
        sa.CheckConstraint(
            "route IN ('local', 'global', 'multi_hop', 'temporal', 'comparison')",
            name="ck_query_execution_trace_route",
        ),
        sa.CheckConstraint(
            "subquery_count >= 0",
            name="ck_query_execution_trace_subqueries",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_query_execution_traces_user_created",
        "query_execution_traces",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_query_execution_traces_user_created",
        table_name="query_execution_traces",
    )
    op.drop_table("query_execution_traces")