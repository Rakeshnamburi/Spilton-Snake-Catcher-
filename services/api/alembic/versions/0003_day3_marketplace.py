"""Day 3 LGD directory, rescuer marketplace, bookings, and notifications.

Revision ID: 0003_day3_marketplace
Revises: 0002_day2_incident_tracking
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_day3_marketplace"
down_revision = "0002_day2_incident_tracking"
branch_labels = None
depends_on = None

VERIFICATION_VALUES = (
    "PENDING",
    "PENDING_VERIFICATION",
    "UNDER_REVIEW",
    "VERIFIED",
    "REJECTED",
    "SUSPENDED",
    "EXPIRED",
)
AVAILABILITY_VALUES = ("AVAILABLE", "BUSY", "OFFLINE")
BOOKING_VALUES = (
    "REQUESTED",
    "PENDING_RESCUER_RESPONSE",
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
    "EN_ROUTE",
    "ARRIVED",
    "IN_PROGRESS",
    "COMPLETED",
    "UNABLE_TO_ASSIST",
)
PAYMENT_VALUES = ("DISABLED", "NOT_REQUIRED", "PENDING", "PAID", "FAILED")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        )
    ]


def _create_location_tables() -> None:
    def common() -> list[sa.Column]:
        return [
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("lgd_code", sa.String(20), nullable=False, unique=True),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("local_name", sa.String(180)),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("source_version", sa.String(100), nullable=False),
            sa.Column(
                "imported_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            *_timestamps(),
        ]

    op.create_table(
        "states",
        *common(),
        sa.Column("is_union_territory", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_states_lgd_code", "states", ["lgd_code"])
    op.create_index("ix_states_name", "states", ["name"])
    op.create_index("ix_states_is_active", "states", ["is_active"])

    op.create_table(
        "districts",
        *common(),
        sa.Column(
            "state_code",
            sa.String(20),
            sa.ForeignKey("states.lgd_code", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_index("ix_districts_lgd_code", "districts", ["lgd_code"])
    op.create_index("ix_districts_state_code", "districts", ["state_code"])
    op.create_index("ix_districts_name", "districts", ["name"])
    op.create_index("ix_districts_is_active", "districts", ["is_active"])
    op.create_index(
        "ix_district_state_active_name", "districts", ["state_code", "is_active", "name"]
    )

    op.create_table(
        "subdistricts",
        *common(),
        sa.Column(
            "district_code",
            sa.String(20),
            sa.ForeignKey("districts.lgd_code", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_index("ix_subdistricts_lgd_code", "subdistricts", ["lgd_code"])
    op.create_index("ix_subdistricts_district_code", "subdistricts", ["district_code"])
    op.create_index("ix_subdistricts_name", "subdistricts", ["name"])
    op.create_index("ix_subdistricts_is_active", "subdistricts", ["is_active"])
    op.create_index(
        "ix_subdistrict_district_active_name",
        "subdistricts",
        ["district_code", "is_active", "name"],
    )

    op.create_table(
        "villages",
        *common(),
        sa.Column(
            "subdistrict_code",
            sa.String(20),
            sa.ForeignKey("subdistricts.lgd_code", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_index("ix_villages_lgd_code", "villages", ["lgd_code"])
    op.create_index("ix_villages_subdistrict_code", "villages", ["subdistrict_code"])
    op.create_index("ix_villages_name", "villages", ["name"])
    op.create_index("ix_villages_is_active", "villages", ["is_active"])
    op.create_index(
        "ix_village_subdistrict_active_name",
        "villages",
        ["subdistrict_code", "is_active", "name"],
    )

    op.create_table(
        "urban_local_bodies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lgd_code", sa.String(20), nullable=False, unique=True),
        sa.Column(
            "state_code",
            sa.String(20),
            sa.ForeignKey("states.lgd_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "district_code",
            sa.String(20),
            sa.ForeignKey("districts.lgd_code", ondelete="RESTRICT"),
        ),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("local_body_type", sa.String(100)),
        sa.Column("local_name", sa.String(180)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column(
            "imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_timestamps(),
    )
    for name, columns in (
        ("ix_urban_local_bodies_lgd_code", ["lgd_code"]),
        ("ix_urban_local_bodies_state_code", ["state_code"]),
        ("ix_urban_local_bodies_district_code", ["district_code"]),
        ("ix_urban_local_bodies_name", ["name"]),
        ("ix_urban_local_bodies_is_active", ["is_active"]),
        ("ix_ulb_state_district_active", ["state_code", "district_code", "is_active"]),
    ):
        op.create_index(name, "urban_local_bodies", columns)

    op.create_table(
        "wards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lgd_code", sa.String(30), nullable=False, unique=True),
        sa.Column(
            "urban_local_body_code",
            sa.String(20),
            sa.ForeignKey("urban_local_bodies.lgd_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("local_name", sa.String(180)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column(
            "imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_timestamps(),
    )
    op.create_index("ix_wards_lgd_code", "wards", ["lgd_code"])
    op.create_index("ix_wards_urban_local_body_code", "wards", ["urban_local_body_code"])
    op.create_index("ix_wards_name", "wards", ["name"])
    op.create_index("ix_wards_is_active", "wards", ["is_active"])
    op.create_index(
        "ix_ward_ulb_active_name", "wards", ["urban_local_body_code", "is_active", "name"]
    )

    op.create_table(
        "location_import_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("rows_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    for column in ("entity_type", "source_version", "source_sha256", "status"):
        op.create_index(f"ix_location_import_jobs_{column}", "location_import_jobs", [column])


def _extend_rescuer_profiles() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for value in VERIFICATION_VALUES[1:]:
                op.execute(f"ALTER TYPE verificationstatus ADD VALUE IF NOT EXISTS '{value}'")

    availability = sa.Enum(*AVAILABILITY_VALUES, name="availabilitystatus")
    if bind.dialect.name == "postgresql":
        availability.create(bind, checkfirst=True)

    columns = [
        sa.Column("public_display_name", sa.String(120)),
        sa.Column("profile_photo_key", sa.String(255)),
        sa.Column("state_code", sa.String(20)),
        sa.Column("district_code", sa.String(20)),
        sa.Column("subdistrict_code", sa.String(20)),
        sa.Column("village_code", sa.String(20)),
        sa.Column("organization_name", sa.String(180)),
        sa.Column("years_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("languages", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("training_details", sa.Text()),
        sa.Column("issuing_authority", sa.String(180)),
        sa.Column("authorization_issue_date", sa.Date()),
        sa.Column("service_area_description", sa.String(500), server_default="", nullable=False),
        sa.Column("service_radius_km", sa.Float(), server_default="25", nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column(
            "availability",
            availability,
            server_default="OFFLINE",
            nullable=False,
        ),
        sa.Column("operating_hours", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("availability_updated_at", sa.DateTime(timezone=True)),
        sa.Column("average_rating", sa.Numeric(3, 2), server_default="0.00", nullable=False),
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_service_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("rescuer_profiles") as batch_op:
            batch_op.alter_column("organization_id", existing_type=sa.Uuid(), nullable=True)
            for column in columns:
                batch_op.add_column(column)
    else:
        op.alter_column(
            "rescuer_profiles", "organization_id", existing_type=sa.Uuid(), nullable=True
        )
        for column in columns:
            op.add_column("rescuer_profiles", column)

    for name, columns in (
        ("ix_rescuer_profiles_organization_id", ["organization_id"]),
        ("ix_rescuer_profiles_verification_status", ["verification_status"]),
        ("ix_rescuer_profiles_state_code", ["state_code"]),
        ("ix_rescuer_profiles_district_code", ["district_code"]),
        ("ix_rescuer_profiles_availability", ["availability"]),
        ("ix_rescuer_profiles_is_demo", ["is_demo"]),
    ):
        op.create_index(name, "rescuer_profiles", columns)

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE INDEX ix_rescuer_service_geography
            ON rescuer_profiles USING GIST (
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
            )
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """
        )


def _create_rescuer_tables() -> None:
    op.create_table(
        "rescuer_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescuer_profile_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("file_size > 0", name="ck_rescuer_document_file_size"),
    )
    op.create_index(
        "ix_rescuer_documents_rescuer_profile_id", "rescuer_documents", ["rescuer_profile_id"]
    )

    op.create_table(
        "rescuer_verification_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescuer_profile_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("previous_status", sa.String(40)),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("note", sa.String(500)),
        *_timestamps(),
    )
    op.create_index(
        "ix_rescuer_verification_history_rescuer_profile_id",
        "rescuer_verification_history",
        ["rescuer_profile_id"],
    )
    op.create_index(
        "ix_rescuer_verification_history_actor_id", "rescuer_verification_history", ["actor_id"]
    )
    op.create_index(
        "ix_rescuer_verification_history_new_status",
        "rescuer_verification_history",
        ["new_status"],
    )

    op.create_table(
        "availability_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rescuer_profile_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(30)),
        sa.Column("new_status", sa.String(30), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_availability_history_rescuer_profile_id",
        "availability_history",
        ["rescuer_profile_id"],
    )
    op.create_index("ix_availability_history_new_status", "availability_history", ["new_status"])


def _create_booking_tables() -> None:
    booking_status = sa.Enum(*BOOKING_VALUES, name="bookingstatus")
    payment_status = sa.Enum(*PAYMENT_VALUES, name="paymentstatus")
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("booking_reference", sa.String(32), nullable=False, unique=True),
        sa.Column(
            "customer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "rescuer_id",
            sa.Uuid(),
            sa.ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="RESTRICT")
        ),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="SET NULL")),
        sa.Column("location_id", sa.Uuid(), sa.ForeignKey("villages.id", ondelete="SET NULL")),
        sa.Column("state_code", sa.String(20)),
        sa.Column("district_code", sa.String(20)),
        sa.Column("subdistrict_code", sa.String(20)),
        sa.Column("village_code", sa.String(20)),
        sa.Column("manual_address", sa.String(500)),
        sa.Column("landmark", sa.String(200)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("location_accuracy", sa.Float()),
        sa.Column("customer_notes", sa.Text(), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column("quoted_amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column(
            "commission_rate_snapshot", sa.Numeric(5, 2), server_default="10.00", nullable=False
        ),
        sa.Column("payment_status", payment_status, nullable=False),
        sa.Column("idempotency_key_hash", sa.String(64)),
        sa.Column("idempotency_request_hash", sa.String(64)),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_timestamps(),
        sa.UniqueConstraint(
            "customer_id", "idempotency_key_hash", name="uq_booking_customer_idempotency"
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_booking_latitude",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_booking_longitude",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_booking_coordinate_pair",
        ),
    )
    for name, columns in (
        ("ix_bookings_booking_reference", ["booking_reference"]),
        ("ix_bookings_customer_id", ["customer_id"]),
        ("ix_bookings_rescuer_id", ["rescuer_id"]),
        ("ix_bookings_organization_id", ["organization_id"]),
        ("ix_bookings_incident_id", ["incident_id"]),
        ("ix_bookings_location_id", ["location_id"]),
        ("ix_bookings_state_code", ["state_code"]),
        ("ix_bookings_district_code", ["district_code"]),
        ("ix_bookings_status", ["status"]),
        ("ix_bookings_is_demo", ["is_demo"]),
        ("ix_booking_customer_created", ["customer_id", "created_at"]),
        ("ix_booking_rescuer_status_created", ["rescuer_id", "status", "created_at"]),
    ):
        op.create_index(name, "bookings", columns)

    for table_name, status_column in (
        ("booking_events", "event_type"),
        ("booking_status_history", "status"),
    ):
        columns = [
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "booking_id",
                sa.Uuid(),
                sa.ForeignKey("bookings.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        ]
        if table_name == "booking_events":
            columns += [
                sa.Column("event_type", sa.String(80), nullable=False),
                sa.Column("details", sa.String(500), nullable=False),
            ]
        else:
            columns += [
                sa.Column("previous_status", sa.String(40)),
                sa.Column("status", sa.String(40), nullable=False),
                sa.Column("note", sa.String(500)),
            ]
        op.create_table(table_name, *columns, *_timestamps())
        op.create_index(f"ix_{table_name}_booking_id", table_name, ["booking_id"])
        op.create_index(f"ix_{table_name}_{status_column}", table_name, [status_column])


def _create_notification_and_pricing_tables() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("template_key", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("subject_template", sa.String(200)),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("template_key", "channel", name="uq_notification_template_channel"),
    )
    op.create_index(
        "ix_notification_templates_template_key", "notification_templates", ["template_key"]
    )

    op.create_table(
        "notification_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "recipient_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("bookings.id", ondelete="CASCADE")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    for column in ("recipient_id", "booking_id", "event_type"):
        op.create_index(f"ix_notification_events_{column}", "notification_events", [column])

    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "notification_event_id",
            sa.Uuid(),
            sa.ForeignKey("notification_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("sanitized_result", sa.String(500)),
        *_timestamps(),
    )
    for column in ("notification_event_id", "channel", "status"):
        op.create_index(
            f"ix_notification_delivery_attempts_{column}",
            "notification_delivery_attempts",
            [column],
        )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("user_id", "channel", name="uq_notification_preference_channel"),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])

    op.create_table(
        "service_pricing_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("state_code", sa.String(20)),
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE")
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("legally_authorized", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_timestamps(),
    )
    for column in ("state_code", "organization_id", "legally_authorized"):
        op.create_index(f"ix_service_pricing_rules_{column}", "service_pricing_rules", [column])

    op.create_table(
        "commission_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("percentage", sa.Numeric(5, 2), server_default="10.00", nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("legally_authorized", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_commission_rules_legally_authorized", "commission_rules", ["legally_authorized"]
    )

    op.create_table(
        "booking_financial_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Uuid(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("service_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 2), server_default="10.00", nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("rescuer_share", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("pricing_authorized", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_illustrative", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_booking_financial_snapshots_booking_id", "booking_financial_snapshots", ["booking_id"]
    )


def upgrade() -> None:
    _create_location_tables()
    _extend_rescuer_profiles()
    _create_rescuer_tables()
    _create_booking_tables()
    _create_notification_and_pricing_tables()


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "booking_financial_snapshots",
        "commission_rules",
        "service_pricing_rules",
        "notification_preferences",
        "notification_delivery_attempts",
        "notification_events",
        "notification_templates",
        "booking_status_history",
        "booking_events",
        "bookings",
        "availability_history",
        "rescuer_verification_history",
        "rescuer_documents",
    ):
        op.drop_table(table)

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_rescuer_service_geography")
    for name in (
        "ix_rescuer_profiles_is_demo",
        "ix_rescuer_profiles_availability",
        "ix_rescuer_profiles_district_code",
        "ix_rescuer_profiles_state_code",
        "ix_rescuer_profiles_verification_status",
        "ix_rescuer_profiles_organization_id",
    ):
        op.drop_index(name, table_name="rescuer_profiles")
    new_columns = (
        "updated_at",
        "is_demo",
        "completed_service_count",
        "review_count",
        "average_rating",
        "availability_updated_at",
        "last_seen_at",
        "operating_hours",
        "availability",
        "longitude",
        "latitude",
        "service_radius_km",
        "service_area_description",
        "authorization_issue_date",
        "issuing_authority",
        "training_details",
        "languages",
        "years_experience",
        "organization_name",
        "village_code",
        "subdistrict_code",
        "district_code",
        "state_code",
        "profile_photo_key",
        "public_display_name",
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("rescuer_profiles") as batch_op:
            for column in new_columns:
                batch_op.drop_column(column)
            batch_op.alter_column("organization_id", existing_type=sa.Uuid(), nullable=False)
    else:
        for column in new_columns:
            op.drop_column("rescuer_profiles", column)
        op.alter_column(
            "rescuer_profiles", "organization_id", existing_type=sa.Uuid(), nullable=False
        )

    for table in (
        "location_import_jobs",
        "wards",
        "urban_local_bodies",
        "villages",
        "subdistricts",
        "districts",
        "states",
    ):
        op.drop_table(table)

    if bind.dialect.name == "postgresql":
        sa.Enum(*AVAILABILITY_VALUES, name="availabilitystatus").drop(bind, checkfirst=True)
        sa.Enum(*BOOKING_VALUES, name="bookingstatus").drop(bind, checkfirst=True)
        sa.Enum(*PAYMENT_VALUES, name="paymentstatus").drop(bind, checkfirst=True)
