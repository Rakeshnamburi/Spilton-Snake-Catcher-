"""Day 5 rescue completion, evidence, demo finance, and reviews.

Revision ID: 0005_day5_completion_finance_reviews
Revises: 0004_day4_realtime_tracking
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0005_day5_completion_finance_reviews"
down_revision = "0004_day4_realtime_tracking"
branch_labels = None
depends_on = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _updated_at() -> sa.Column:
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _index(table: str, *columns: str, name: str | None = None) -> None:
    op.create_index(name or f"ix_{table}_{'_'.join(columns)}", table, list(columns))


def _extend_bookings() -> None:
    columns = [
        sa.Column("arrived_at", sa.DateTime(timezone=True)),
        sa.Column("arrival_latitude", sa.Float()),
        sa.Column("arrival_longitude", sa.Float()),
        sa.Column("arrival_accuracy", sa.Float()),
        sa.Column(
            "arrival_review_warning", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("customer_confirmed_at", sa.DateTime(timezone=True)),
    ]
    constraints = [
        sa.CheckConstraint(
            "(arrival_latitude IS NULL AND arrival_longitude IS NULL) OR "
            "(arrival_latitude IS NOT NULL AND arrival_longitude IS NOT NULL)",
            name="ck_booking_arrival_coordinate_pair",
        ),
        sa.CheckConstraint(
            "arrival_latitude IS NULL OR (arrival_latitude >= -90 AND arrival_latitude <= 90)",
            name="ck_booking_arrival_latitude",
        ),
        sa.CheckConstraint(
            "arrival_longitude IS NULL OR (arrival_longitude >= -180 AND arrival_longitude <= 180)",
            name="ck_booking_arrival_longitude",
        ),
        sa.CheckConstraint(
            "arrival_accuracy IS NULL OR (arrival_accuracy >= 0 AND arrival_accuracy <= 10000)",
            name="ck_booking_arrival_accuracy",
        ),
    ]
    with op.batch_alter_table("bookings") as batch:
        for column in columns:
            batch.add_column(column)
        for constraint in constraints:
            batch.create_check_constraint(constraint.name, constraint.sqltext)


def _create_rescue_tables() -> None:
    op.create_table(
        "rescue_outcomes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(60), nullable=False, unique=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
    )
    _index("rescue_outcomes", "code")
    _index("rescue_outcomes", "is_active")
    outcome_table = sa.table(
        "rescue_outcomes",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("label", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    # Stable synthetic UUIDs keep tests and repeated environments deterministic.
    op.bulk_insert(
        outcome_table,
        [
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000501"),
                "code": "SNAKE_NO_LONGER_VISIBLE",
                "label": "Snake no longer visible",
                "description": "The area was assessed but the snake was no longer visible.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000502"),
                "code": "AREA_INSPECTED",
                "label": "Area inspected",
                "description": (
                    "The reported area was inspected without claiming capture or relocation."
                ),
                "is_active": True,
            },
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000503"),
                "code": "OBSERVED_NO_INTERVENTION",
                "label": "Observed without intervention",
                "description": (
                    "The snake was observed from a safe distance and no intervention was recorded."
                ),
                "is_active": True,
            },
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000504"),
                "code": "AUTHORIZED_RESCUE_COMPLETED",
                "label": "Authorized rescue completed",
                "description": (
                    "A demo record representing an authorized partner workflow completion."
                ),
                "is_active": True,
            },
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000505"),
                "code": "REFERRED_FOREST_DEPARTMENT",
                "label": "Referred to Forest Department",
                "description": "The workflow was referred to the appropriate public authority.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000506"),
                "code": "UNABLE_TO_ASSIST",
                "label": "Unable to assist",
                "description": "The simulated service could not be completed.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("00000000-0000-4000-8000-000000000507"),
                "code": "OTHER_DOCUMENTED_OUTCOME",
                "label": "Other documented outcome",
                "description": "A different outcome was documented without assuming capture.",
                "is_active": True,
            },
        ],
    )

    op.create_table(
        "rescue_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "rescuer_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
        ),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), server_default="IN_PROGRESS", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        _updated_at(),
    )
    for column in (
        "booking_id",
        "rescuer_id",
        "organization_id",
        "incident_id",
        "status",
        "is_demo",
    ):
        _index("rescue_sessions", column)

    op.create_table(
        "rescue_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescue_session_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
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
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "outcome_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_outcomes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observations", sa.Text(), nullable=False),
        sa.Column("authorized_action_summary", sa.Text(), nullable=False),
        sa.Column("referral_details", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("species_text", sa.String(160)),
        sa.Column(
            "species_verification", sa.String(40), server_default="UNVERIFIED", nullable=False
        ),
        sa.Column("completion_status", sa.String(40), server_default="SUBMITTED", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(64), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("booking_id", name="uq_rescue_report_booking"),
        sa.UniqueConstraint(
            "rescuer_id", "idempotency_key_hash", name="uq_rescue_report_rescuer_idempotency"
        ),
    )
    for column in (
        "rescue_session_id",
        "booking_id",
        "rescuer_id",
        "organization_id",
        "outcome_id",
        "species_verification",
        "completion_status",
        "is_demo",
    ):
        _index("rescue_reports", column)

    op.create_table(
        "rescue_report_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescue_report_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details", sa.String(500), nullable=False),
        _created_at(),
    )
    for column in ("rescue_report_id", "actor_id", "event_type"):
        _index("rescue_report_events", column)

    op.create_table(
        "rescue_media",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rescue_session_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploader_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "malware_scan_status",
            sa.String(30),
            server_default="NOT_CONFIGURED",
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        sa.CheckConstraint("file_size > 0", name="ck_rescue_media_file_size"),
    )
    for column in (
        "booking_id",
        "rescue_session_id",
        "uploader_id",
        "evidence_type",
        "retention_expires_at",
        "malware_scan_status",
        "is_demo",
    ):
        _index("rescue_media", column)
    _index("rescue_media", "booking_id", "evidence_type", name="ix_rescue_media_booking_type")

    op.create_table(
        "evidence_location_metadata",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescue_media_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_media.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("association_only", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_evidence_location_latitude"
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_evidence_location_longitude"
        ),
        sa.CheckConstraint(
            "accuracy >= 0 AND accuracy <= 10000", name="ck_evidence_location_accuracy"
        ),
    )
    _index("evidence_location_metadata", "rescue_media_id")

    op.create_table(
        "evidence_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescue_media_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_media.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("details", sa.String(500), nullable=False),
        _created_at(),
    )
    for column in ("rescue_media_id", "actor_id", "action"):
        _index("evidence_audit_events", column)

    op.create_table(
        "completion_disputes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(40), server_default="OPEN", nullable=False),
        sa.Column("coordinator_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolution_note", sa.String(1000)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
    )
    for column in ("booking_id", "customer_id", "status", "coordinator_id", "is_demo"):
        _index("completion_disputes", column)


def _create_finance_tables() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payment_reference", sa.String(40), nullable=False, unique=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("provider_reference", sa.String(120)),
        sa.Column("idempotency_key_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(64), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("refunded_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint(
            "customer_id", "idempotency_key_hash", name="uq_payment_customer_idempotency"
        ),
    )
    for column in (
        "payment_reference",
        "booking_id",
        "customer_id",
        "method",
        "status",
        "is_demo",
    ):
        _index("payments", column)

    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("sanitized_result", sa.String(500), nullable=False),
        _created_at(),
    )
    _index("payment_attempts", "payment_id")
    _index("payment_attempts", "status")

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details", sa.String(500), nullable=False),
        _created_at(),
    )
    for column in ("payment_id", "actor_id", "event_type"):
        _index("payment_events", column)

    op.create_table(
        "payment_refunds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            sa.ForeignKey("payments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(40), server_default="DEMO_REFUNDED", nullable=False),
        sa.Column("idempotency_key_hash", sa.String(64), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        sa.UniqueConstraint(
            "payment_id", "idempotency_key_hash", name="uq_refund_payment_idempotency"
        ),
    )
    for column in ("payment_id", "status", "is_demo"):
        _index("payment_refunds", column)

    op.create_table(
        "payment_provider_webhooks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("event_reference", sa.String(160), nullable=False, unique=True),
        sa.Column("signature_valid", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sanitized_status", sa.String(80), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
    )
    _index("payment_provider_webhooks", "provider")
    _index("payment_provider_webhooks", "event_reference")

    op.create_table(
        "commission_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            sa.ForeignKey("payments.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rate_snapshot", sa.Numeric(5, 2), nullable=False),
        sa.Column("eligible_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("rescuer_share", sa.Numeric(12, 2), nullable=False),
        sa.Column("reversed_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(40), server_default="DEMO_RECORDED", nullable=False),
        sa.Column("settlement_status", sa.String(40), server_default="NOT_SETTLED", nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
    )
    for column in (
        "payment_id",
        "booking_id",
        "status",
        "settlement_status",
        "is_demo",
    ):
        _index("commission_entries", column)

    op.create_table(
        "settlement_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescuer_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("status", sa.String(40), server_default="DEMO_ONLY", nullable=False),
        sa.Column("withdrawable", sa.Boolean(), server_default=sa.false(), nullable=False),
        _created_at(),
        sa.UniqueConstraint("rescuer_id", "currency", name="uq_settlement_rescuer_currency"),
    )
    _index("settlement_accounts", "rescuer_id")
    _index("settlement_accounts", "status")

    op.create_table(
        "settlement_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "settlement_account_id",
            sa.Uuid(),
            sa.ForeignKey("settlement_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "commission_entry_id",
            sa.Uuid(),
            sa.ForeignKey("commission_entries.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(40), server_default="PENDING_DEMO", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
    )
    for column in ("settlement_account_id", "commission_entry_id", "status"):
        _index("settlement_entries", column)

    op.create_table(
        "financial_ledger_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_group", sa.String(64), nullable=False),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            sa.ForeignKey("payments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_code", sa.String(60), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        sa.CheckConstraint("amount >= 0", name="ck_financial_ledger_amount"),
        sa.CheckConstraint(
            "direction IN ('DEBIT', 'CREDIT')", name="ck_financial_ledger_direction"
        ),
    )
    for column in (
        "transaction_group",
        "payment_id",
        "booking_id",
        "account_code",
        "direction",
        "is_demo",
    ):
        _index("financial_ledger_entries", column)
    _index(
        "financial_ledger_entries",
        "transaction_group",
        "created_at",
        name="ix_ledger_transaction_group",
    )


def _create_review_tables() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "rescuer_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.String(1000)),
        sa.Column(
            "moderation_status", sa.String(40), server_default="PUBLISHED_DEMO", nullable=False
        ),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        sa.UniqueConstraint("booking_id", name="uq_review_booking"),
    )
    for column in (
        "booking_id",
        "customer_id",
        "rescuer_id",
        "moderation_status",
        "is_demo",
    ):
        _index("reviews", column)

    op.create_table(
        "review_abuse_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "review_id",
            sa.Uuid(),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reporter_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(40), server_default="OPEN", nullable=False),
        sa.Column("resolved_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolution_note", sa.String(500)),
        _created_at(),
        sa.UniqueConstraint("review_id", "reporter_id", name="uq_review_reporter"),
    )
    for column in ("review_id", "reporter_id", "status"):
        _index("review_abuse_reports", column)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'DISPUTED'")
    _extend_bookings()
    _create_rescue_tables()
    _create_finance_tables()
    _create_review_tables()


def downgrade() -> None:
    for table in (
        "review_abuse_reports",
        "reviews",
        "financial_ledger_entries",
        "settlement_entries",
        "settlement_accounts",
        "commission_entries",
        "payment_provider_webhooks",
        "payment_refunds",
        "payment_events",
        "payment_attempts",
        "payments",
        "completion_disputes",
        "evidence_audit_events",
        "evidence_location_metadata",
        "rescue_media",
        "rescue_report_events",
        "rescue_reports",
        "rescue_sessions",
        "rescue_outcomes",
    ):
        op.drop_table(table)
    with op.batch_alter_table("bookings") as batch:
        for constraint in (
            "ck_booking_arrival_accuracy",
            "ck_booking_arrival_longitude",
            "ck_booking_arrival_latitude",
            "ck_booking_arrival_coordinate_pair",
        ):
            batch.drop_constraint(constraint, type_="check")
        for column in (
            "customer_confirmed_at",
            "completed_at",
            "arrival_review_warning",
            "arrival_accuracy",
            "arrival_longitude",
            "arrival_latitude",
            "arrived_at",
        ):
            batch.drop_column(column)
    # PostgreSQL enum values are intentionally not removed during downgrade.
