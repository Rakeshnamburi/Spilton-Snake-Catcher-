"""Day 2 GPS, triage, media, idempotency, and incident workflow.

Revision ID: 0002_day2_incident_tracking
Revises: 0001_initial
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_day2_incident_tracking"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

OLD_STATUSES = ("RECEIVED", "REVIEWING", "CLOSED")
NEW_STATUSES = (
    "CREATED",
    "UNDER_REVIEW",
    "ASSIGNED",
    "IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
    "CANCELLED",
    "UNABLE_TO_ASSIST",
)


def _add_incident_columns() -> None:
    op.add_column("incidents", sa.Column("reporter_email", sa.String(255), nullable=True))
    op.add_column("incidents", sa.Column("landmark", sa.String(200), nullable=True))
    op.add_column("incidents", sa.Column("address_description", sa.String(500), nullable=True))
    op.add_column("incidents", sa.Column("sighting_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("injury_reported", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "incidents",
        sa.Column("snake_visible", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "incidents",
        sa.Column("immediate_danger", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("incidents", sa.Column("idempotency_key_hash", sa.String(64), nullable=True))
    op.add_column("incidents", sa.Column("idempotency_request_hash", sa.String(64), nullable=True))
    op.execute(sa.text("UPDATE incidents SET sighting_at = created_at WHERE sighting_at IS NULL"))


def _upgrade_postgresql_status() -> None:
    new_enum = postgresql.ENUM(*NEW_STATUSES, name="incidentstatus_v2")
    new_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE incidents
        ALTER COLUMN status TYPE incidentstatus_v2
        USING (
            CASE status::text
                WHEN 'RECEIVED' THEN 'CREATED'
                WHEN 'REVIEWING' THEN 'UNDER_REVIEW'
                ELSE status::text
            END
        )::incidentstatus_v2
        """
    )
    postgresql.ENUM(*OLD_STATUSES, name="incidentstatus").drop(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE incidentstatus_v2 RENAME TO incidentstatus")


def _upgrade_other_status() -> None:
    op.execute("UPDATE incidents SET status = 'CREATED' WHERE status = 'RECEIVED'")
    op.execute("UPDATE incidents SET status = 'UNDER_REVIEW' WHERE status = 'REVIEWING'")


def _create_incident_media() -> None:
    op.create_table(
        "incident_media",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "incident_id",
            sa.Uuid(),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("file_size > 0", name="ck_incident_media_file_size"),
    )
    op.create_index("ix_incident_media_incident_id", "incident_media", ["incident_id"])


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    _add_incident_columns()

    if dialect == "postgresql":
        _upgrade_postgresql_status()
        op.alter_column(
            "incidents",
            "reference_code",
            existing_type=sa.String(20),
            type_=sa.String(32),
            existing_nullable=False,
        )
        op.alter_column(
            "incidents",
            "sighting_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        op.create_unique_constraint(
            "uq_incident_owner_idempotency",
            "incidents",
            ["reporter_id", "idempotency_key_hash"],
        )
        op.create_check_constraint(
            "ck_incident_latitude",
            "incidents",
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
        )
        op.create_check_constraint(
            "ck_incident_longitude",
            "incidents",
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
        )
        op.create_check_constraint(
            "ck_incident_location_accuracy",
            "incidents",
            "location_accuracy IS NULL OR location_accuracy >= 0",
        )
        op.create_check_constraint(
            "ck_incident_coordinate_pair",
            "incidents",
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
        )
    else:
        _upgrade_other_status()
        with op.batch_alter_table("incidents", recreate="always") as batch_op:
            batch_op.alter_column(
                "reference_code",
                existing_type=sa.String(20),
                type_=sa.String(32),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "sighting_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(*OLD_STATUSES, name="incidentstatus"),
                type_=sa.Enum(*NEW_STATUSES, name="incidentstatus"),
                existing_nullable=False,
            )
            batch_op.create_unique_constraint(
                "uq_incident_owner_idempotency", ["reporter_id", "idempotency_key_hash"]
            )
            batch_op.create_check_constraint(
                "ck_incident_latitude", "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)"
            )
            batch_op.create_check_constraint(
                "ck_incident_longitude",
                "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            )
            batch_op.create_check_constraint(
                "ck_incident_location_accuracy",
                "location_accuracy IS NULL OR location_accuracy >= 0",
            )
            batch_op.create_check_constraint(
                "ck_incident_coordinate_pair",
                "(latitude IS NULL AND longitude IS NULL) OR "
                "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            )

    _create_incident_media()


def _downgrade_postgresql_status() -> None:
    old_enum = postgresql.ENUM(*OLD_STATUSES, name="incidentstatus_v1")
    old_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE incidents
        ALTER COLUMN status TYPE incidentstatus_v1
        USING (
            CASE status::text
                WHEN 'CREATED' THEN 'RECEIVED'
                WHEN 'UNDER_REVIEW' THEN 'REVIEWING'
                WHEN 'ASSIGNED' THEN 'REVIEWING'
                WHEN 'IN_PROGRESS' THEN 'REVIEWING'
                WHEN 'RESOLVED' THEN 'REVIEWING'
                WHEN 'UNABLE_TO_ASSIST' THEN 'REVIEWING'
                ELSE 'CLOSED'
            END
        )::incidentstatus_v1
        """
    )
    postgresql.ENUM(*NEW_STATUSES, name="incidentstatus").drop(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE incidentstatus_v1 RENAME TO incidentstatus")


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    op.drop_index("ix_incident_media_incident_id", table_name="incident_media")
    op.drop_table("incident_media")

    if dialect == "postgresql":
        op.drop_constraint("ck_incident_coordinate_pair", "incidents", type_="check")
        op.drop_constraint("ck_incident_location_accuracy", "incidents", type_="check")
        op.drop_constraint("ck_incident_longitude", "incidents", type_="check")
        op.drop_constraint("ck_incident_latitude", "incidents", type_="check")
        op.drop_constraint("uq_incident_owner_idempotency", "incidents", type_="unique")
        _downgrade_postgresql_status()
        op.alter_column(
            "incidents",
            "reference_code",
            existing_type=sa.String(32),
            type_=sa.String(20),
            existing_nullable=False,
        )
        for column in (
            "idempotency_request_hash",
            "idempotency_key_hash",
            "immediate_danger",
            "snake_visible",
            "injury_reported",
            "sighting_at",
            "address_description",
            "landmark",
            "reporter_email",
        ):
            op.drop_column("incidents", column)
    else:
        op.execute(
            """
            UPDATE incidents SET status = CASE status
                WHEN 'CREATED' THEN 'RECEIVED'
                WHEN 'UNDER_REVIEW' THEN 'REVIEWING'
                WHEN 'ASSIGNED' THEN 'REVIEWING'
                WHEN 'IN_PROGRESS' THEN 'REVIEWING'
                WHEN 'RESOLVED' THEN 'REVIEWING'
                WHEN 'UNABLE_TO_ASSIST' THEN 'REVIEWING'
                ELSE 'CLOSED' END
            """
        )
        with op.batch_alter_table("incidents", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_incident_coordinate_pair", type_="check")
            batch_op.drop_constraint("ck_incident_location_accuracy", type_="check")
            batch_op.drop_constraint("ck_incident_longitude", type_="check")
            batch_op.drop_constraint("ck_incident_latitude", type_="check")
            batch_op.drop_constraint("uq_incident_owner_idempotency", type_="unique")
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(*NEW_STATUSES, name="incidentstatus"),
                type_=sa.Enum(*OLD_STATUSES, name="incidentstatus"),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "reference_code",
                existing_type=sa.String(32),
                type_=sa.String(20),
                existing_nullable=False,
            )
            for column in (
                "idempotency_request_hash",
                "idempotency_key_hash",
                "immediate_danger",
                "snake_visible",
                "injury_reported",
                "sighting_at",
                "address_description",
                "landmark",
                "reporter_email",
            ):
                batch_op.drop_column(column)
