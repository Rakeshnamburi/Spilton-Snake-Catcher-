"""Day 6 session revocation and privacy request workflow.

Revision ID: 0006_day6_release_readiness
Revises: 0005_day5_completion_finance_reviews
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_day6_release_readiness"
down_revision = "0005_day5_completion_finance_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("token_version", sa.Integer(), server_default="0", nullable=False)
        )
    op.create_table(
        "account_data_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), server_default="REQUESTED", nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("processed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "request_type IN ('EXPORT', 'DELETION')", name="ck_account_request_type"
        ),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'UNDER_REVIEW', 'COMPLETED', 'REJECTED')",
            name="ck_account_request_status",
        ),
    )
    op.create_index("ix_account_data_requests_user_id", "account_data_requests", ["user_id"])
    op.create_index(
        "ix_account_data_requests_request_type", "account_data_requests", ["request_type"]
    )
    op.create_index("ix_account_data_requests_status", "account_data_requests", ["status"])
    op.create_index(
        "ix_account_data_request_user_status", "account_data_requests", ["user_id", "status"]
    )


def downgrade() -> None:
    op.drop_table("account_data_requests")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
