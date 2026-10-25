"""Rescuer travel coverage and in-app booking chat.

Revision ID: 0008_rescuer_coverage_chat
Revises: 0007_auth_otp_oauth

Adds rescuer_profiles.coverage_subdistrict_codes (the other mandals a rescuer
will travel to) and a booking_messages table for customer <-> rescuer chat.
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_rescuer_coverage_chat"
down_revision = "0007_auth_otp_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("rescuer_profiles") as batch:
        batch.add_column(
            sa.Column(
                "coverage_subdistrict_codes",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )

    op.create_table(
        "booking_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_role", sa.String(20), nullable=False),
        sa.Column("body", sa.String(1000), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_booking_messages_booking_id", "booking_messages", ["booking_id"])
    op.create_index("ix_booking_messages_sender_id", "booking_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_booking_messages_sender_id", table_name="booking_messages")
    op.drop_index("ix_booking_messages_booking_id", table_name="booking_messages")
    op.drop_table("booking_messages")
    with op.batch_alter_table("rescuer_profiles") as batch:
        batch.drop_column("coverage_subdistrict_codes")
