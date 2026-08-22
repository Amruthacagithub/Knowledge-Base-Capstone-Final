"""Add reviewable temporal claim conflict candidates."""
from alembic import op
import sqlalchemy as sa


revision = "0006_claim_conflicts"
down_revision = "0005_retrieval_traces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claim_conflicts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("claim_a_id", sa.String(), nullable=False),
        sa.Column("claim_b_id", sa.String(), nullable=False),
        sa.Column("conflict_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(), nullable=True),
        sa.CheckConstraint("claim_a_id < claim_b_id", name="ck_claim_conflict_order"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_claim_conflict_confidence",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'confirmed', 'dismissed')",
            name="ck_claim_conflict_status",
        ),
        sa.ForeignKeyConstraint(
            ["claim_a_id"],
            ["evidence_claims.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claim_b_id"],
            ["evidence_claims.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "claim_a_id",
            "claim_b_id",
            "conflict_type",
            name="uq_claim_conflict_pair_type",
        ),
    )
    op.create_index(
        "ix_claim_conflicts_status_created",
        "claim_conflicts",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_claim_conflicts_status_created", table_name="claim_conflicts")
    op.drop_table("claim_conflicts")