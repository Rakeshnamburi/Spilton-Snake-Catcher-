"""initial schema"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

role = sa.Enum("CITIZEN", "RESCUER", "COORDINATOR", "ADMIN", name="role")
verification = sa.Enum("PENDING", "VERIFIED", "REJECTED", name="verificationstatus")
urgency = sa.Enum("STANDARD", "HIGH", "SNAKEBITE", name="urgency")
incident_status = sa.Enum("RECEIVED", "REVIEWING", "CLOSED", name="incidentstatus")


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("organization_type", sa.String(80), nullable=False),
        sa.Column("verification_status", verification, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_organizations_state", "organizations", ["state"])
    op.create_index("ix_organizations_district", "organizations", ["district"])
    op.create_index(
        "ix_organizations_verification_status", "organizations", ["verification_status"]
    )
    op.create_table(
        "rescuer_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("verification_status", verification, nullable=False),
        sa.Column("authorization_reference", sa.String(160)),
        sa.Column("authorization_expiry", sa.Date()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference_code", sa.String(20), nullable=False, unique=True),
        sa.Column(
            "reporter_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("reporter_name", sa.String(120), nullable=False),
        sa.Column("contact_phone", sa.String(20), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("location_accuracy", sa.Float()),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("urgency", urgency, nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for name, cols in [
        ("ix_incidents_reference_code", ["reference_code"]),
        ("ix_incidents_reporter_id", ["reporter_id"]),
        ("ix_incidents_state", ["state"]),
        ("ix_incidents_district", ["district"]),
        ("ix_incidents_urgency", ["urgency"]),
        ("ix_incidents_status", ["status"]),
        ("ix_incidents_is_demo", ["is_demo"]),
        ("ix_incident_owner_created", ["reporter_id", "created_at"]),
    ]:
        op.create_index(name, "incidents", cols)
    op.create_table(
        "incident_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "incident_id",
            sa.Uuid(),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_incident_events_incident_id", "incident_events", ["incident_id"])
    op.create_index("ix_incident_events_event_type", "incident_events", ["event_type"])
    op.create_table(
        "emergency_contacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_name", sa.String(180), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100)),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_contact_region_active", "emergency_contacts", ["state", "district", "is_active"]
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade():
    for table in [
        "audit_logs",
        "emergency_contacts",
        "incident_events",
        "incidents",
        "rescuer_profiles",
        "organizations",
        "users",
    ]:
        op.drop_table(table)
