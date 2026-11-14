"""Email verification for new accounts.

Revision ID: 0009_email_verification
Revises: 0008_rescuer_coverage_chat

Adds users.email_verified_at. Existing accounts are grandfathered as verified so
the change cannot lock anybody out.
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_email_verification"
down_revision = "0008_rescuer_coverage_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    # Grandfather every existing account: they predate email verification.
    op.execute("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified_at")
