"""Email OTP and social (OAuth) sign-in support.

Revision ID: 0007_auth_otp_oauth
Revises: 0006_day6_release_readiness

Adds a hashed one-time-passcode table and an external-identity link table, and
relaxes users.phone / users.password_hash so social/OTP accounts can exist
without a phone number or password.
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_auth_otp_oauth"
down_revision = "0006_day6_release_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("phone", existing_type=sa.String(20), nullable=True)
        batch.alter_column("password_hash", existing_type=sa.String(255), nullable=True)

    op.create_table(
        "oauth_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("display_name", sa.String(120)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )
    op.create_index("ix_oauth_identities_user_id", "oauth_identities", ["user_id"])
    op.create_index("ix_oauth_identities_provider", "oauth_identities", ["provider"])

    op.create_table(
        "auth_otp_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(20), server_default="LOGIN", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_auth_otp_codes_email", "auth_otp_codes", ["email"])


def downgrade() -> None:
    op.drop_index("ix_auth_otp_codes_email", table_name="auth_otp_codes")
    op.drop_table("auth_otp_codes")
    op.drop_index("ix_oauth_identities_provider", table_name="oauth_identities")
    op.drop_index("ix_oauth_identities_user_id", table_name="oauth_identities")
    op.drop_table("oauth_identities")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("phone", existing_type=sa.String(20), nullable=False)
        batch.alter_column("password_hash", existing_type=sa.String(255), nullable=False)
