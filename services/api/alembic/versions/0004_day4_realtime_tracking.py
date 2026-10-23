"""Day 4 notification delivery, device registration, and consent tracking.

Revision ID: 0004_day4_realtime_tracking
Revises: 0003_day3_marketplace
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_day4_realtime_tracking"
down_revision = "0003_day3_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("booking_events") as batch:
        batch.add_column(sa.Column("sequence", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY booking_id ORDER BY created_at, id
                ) AS event_sequence
                FROM booking_events
            )
            UPDATE booking_events
            SET sequence = (
                SELECT event_sequence FROM ranked WHERE ranked.id = booking_events.id
            )
            """
        )
    )
    with op.batch_alter_table("booking_events") as batch:
        batch.alter_column("sequence", existing_type=sa.Integer(), nullable=False)
        batch.create_unique_constraint("uq_booking_event_sequence", ["booking_id", "sequence"])
        batch.create_index(
            "ix_booking_event_booking_sequence", ["booking_id", "sequence"], unique=False
        )

    with op.batch_alter_table("notification_events") as batch:
        batch.add_column(sa.Column("deep_link", sa.String(500), nullable=True))
        batch.add_column(sa.Column("deduplication_key", sa.String(255), nullable=True))
        batch.create_unique_constraint("uq_notification_event_deduplication", ["deduplication_key"])

    with op.batch_alter_table("notification_delivery_attempts") as batch:
        batch.add_column(
            sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch.add_column(
            sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False)
        )
        batch.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("last_attempt_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("provider_message_id", sa.String(255)))
        batch.add_column(sa.Column("error_code", sa.String(80)))
        batch.create_unique_constraint(
            "uq_notification_delivery_channel", ["notification_event_id", "channel"]
        )
        batch.create_index("ix_notification_delivery_attempts_next_attempt_at", ["next_attempt_at"])
        batch.create_index(
            "ix_notification_delivery_attempts_provider_message_id", ["provider_message_id"]
        )

    with op.batch_alter_table("notification_preferences") as batch:
        batch.add_column(sa.Column("opted_in_at", sa.DateTime(timezone=True)))

    op.create_table(
        "device_registrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("token_value", sa.Text(), nullable=False),
        sa.Column("device_label", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "token_hash", name="uq_device_user_token"),
    )
    op.create_index("ix_device_registrations_user_id", "device_registrations", ["user_id"])
    op.create_index("ix_device_registrations_is_active", "device_registrations", ["is_active"])
    op.create_index("ix_device_user_active", "device_registrations", ["user_id", "is_active"])

    tracking_status = sa.Enum("ACTIVE", "PAUSED", "STOPPED", "EXPIRED", name="trackingstatus")
    tracking_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "tracking_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rescuer_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", tracking_status, nullable=False),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_version", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_location_at", sa.DateTime(timezone=True)),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("booking_id", "rescuer_id", "status", "expires_at", "is_demo"):
        op.create_index(f"ix_tracking_sessions_{column}", "tracking_sessions", [column])
    op.create_index("ix_tracking_booking_status", "tracking_sessions", ["booking_id", "status"])
    op.create_index("ix_tracking_rescuer_status", "tracking_sessions", ["rescuer_id", "status"])

    op.create_table(
        "tracking_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tracking_session_id",
            sa.Uuid(),
            sa.ForeignKey("tracking_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_tracking_latitude"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_tracking_longitude"),
        sa.CheckConstraint("accuracy >= 0 AND accuracy <= 10000", name="ck_tracking_accuracy"),
    )
    op.create_index(
        "ix_tracking_locations_tracking_session_id",
        "tracking_locations",
        ["tracking_session_id"],
    )
    op.create_index(
        "ix_tracking_location_session_recorded",
        "tracking_locations",
        ["tracking_session_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_tracking_location_session_recorded", table_name="tracking_locations")
    op.drop_index("ix_tracking_locations_tracking_session_id", table_name="tracking_locations")
    op.drop_table("tracking_locations")
    op.drop_index("ix_tracking_rescuer_status", table_name="tracking_sessions")
    op.drop_index("ix_tracking_booking_status", table_name="tracking_sessions")
    for column in ("is_demo", "expires_at", "status", "rescuer_id", "booking_id"):
        op.drop_index(f"ix_tracking_sessions_{column}", table_name="tracking_sessions")
    op.drop_table("tracking_sessions")
    sa.Enum(name="trackingstatus").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_device_user_active", table_name="device_registrations")
    op.drop_index("ix_device_registrations_is_active", table_name="device_registrations")
    op.drop_index("ix_device_registrations_user_id", table_name="device_registrations")
    op.drop_table("device_registrations")

    with op.batch_alter_table("notification_preferences") as batch:
        batch.drop_column("opted_in_at")
    with op.batch_alter_table("notification_delivery_attempts") as batch:
        batch.drop_index("ix_notification_delivery_attempts_provider_message_id")
        batch.drop_index("ix_notification_delivery_attempts_next_attempt_at")
        batch.drop_constraint("uq_notification_delivery_channel", type_="unique")
        for column in (
            "error_code",
            "provider_message_id",
            "delivered_at",
            "last_attempt_at",
            "next_attempt_at",
            "max_attempts",
            "attempt_count",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("notification_events") as batch:
        batch.drop_constraint("uq_notification_event_deduplication", type_="unique")
        batch.drop_column("deduplication_key")
        batch.drop_column("deep_link")
    with op.batch_alter_table("booking_events") as batch:
        batch.drop_index("ix_booking_event_booking_sequence")
        batch.drop_constraint("uq_booking_event_sequence", type_="unique")
        batch.drop_column("sequence")
