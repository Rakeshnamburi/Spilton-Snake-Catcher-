import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Role(str, enum.Enum):
    CITIZEN = "CITIZEN"
    RESCUER = "RESCUER"
    COORDINATOR = "COORDINATOR"
    ADMIN = "ADMIN"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class BookingStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    PENDING_RESCUER_RESPONSE = "PENDING_RESCUER_RESPONSE"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    UNABLE_TO_ASSIST = "UNABLE_TO_ASSIST"
    DISPUTED = "DISPUTED"


class PaymentStatus(str, enum.Enum):
    DISABLED = "DISABLED"
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"


class TrackingStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"


class Urgency(str, enum.Enum):
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    SNAKEBITE = "SNAKEBITE"


class IncidentStatus(str, enum.Enum):
    CREATED = "CREATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    UNABLE_TO_ASSIST = "UNABLE_TO_ASSIST"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.CITIZEN, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="reporter")


class AccountDataRequest(TimestampMixin, Base):
    __tablename__ = "account_data_requests"
    __table_args__ = (Index("ix_account_data_request_user_status", "user_id", "status"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    request_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED", index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180))
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    organization_type: Mapped[str] = mapped_column(String(80))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.PENDING, index=True
    )


class RescuerProfile(TimestampMixin, Base):
    __tablename__ = "rescuer_profiles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.PENDING_VERIFICATION, index=True
    )
    public_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    profile_photo_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    district_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    subdistrict_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    village_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    training_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorization_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(180), nullable=True)
    authorization_issue_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    authorization_expiry: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    service_area_description: Mapped[str] = mapped_column(String(500), default="")
    service_radius_km: Mapped[float] = mapped_column(Float, default=25.0)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus), default=AvailabilityStatus.OFFLINE, index=True
    )
    operating_hours: Mapped[dict] = mapped_column(JSON, default=dict)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    availability_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    average_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_service_count: Mapped[int] = mapped_column(Integer, default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incident_owner_created", "reporter_id", "created_at"),
        UniqueConstraint(
            "reporter_id", "idempotency_key_hash", name="uq_incident_owner_idempotency"
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_incident_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_incident_longitude",
        ),
        CheckConstraint(
            "location_accuracy IS NULL OR location_accuracy >= 0",
            name="ck_incident_location_accuracy",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_incident_coordinate_pair",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reporter_name: Mapped[str] = mapped_column(String(120))
    contact_phone: Mapped[str] = mapped_column(String(20))
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str] = mapped_column(String(120))
    landmark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    sighting_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    injury_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    snake_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    immediate_danger: Mapped[bool] = mapped_column(Boolean, default=False)
    urgency: Mapped[Urgency] = mapped_column(Enum(Urgency), default=Urgency.STANDARD, index=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.CREATED, index=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    reporter: Mapped[User] = relationship(back_populates="incidents")
    events: Mapped[list["IncidentEvent"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="IncidentEvent.created_at"
    )
    media: Mapped[list["IncidentMedia"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentMedia.uploaded_at",
    )


class IncidentEvent(TimestampMixin, Base):
    __tablename__ = "incident_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(Text)
    incident: Mapped[Incident] = relationship(back_populates="events")


class IncidentMedia(Base):
    __tablename__ = "incident_media"
    __table_args__ = (CheckConstraint("file_size > 0", name="ck_incident_media_file_size"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    incident: Mapped[Incident] = relationship(back_populates="media")


class EmergencyContact(TimestampMixin, Base):
    __tablename__ = "emergency_contacts"
    __table_args__ = (Index("ix_contact_region_active", "state", "district", "is_active"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_name: Mapped[str] = mapped_column(String(180))
    state: Mapped[str] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(20))
    source_url: Mapped[str] = mapped_column(String(500))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(64))


class State(TimestampMixin, Base):
    __tablename__ = "states"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lgd_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    local_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_union_territory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_version: Mapped[str] = mapped_column(String(100))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class District(TimestampMixin, Base):
    __tablename__ = "districts"
    __table_args__ = (Index("ix_district_state_active_name", "state_code", "is_active", "name"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lgd_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    state_code: Mapped[str] = mapped_column(
        ForeignKey("states.lgd_code", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(180), index=True)
    local_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_version: Mapped[str] = mapped_column(String(100))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Subdistrict(TimestampMixin, Base):
    __tablename__ = "subdistricts"
    __table_args__ = (
        Index("ix_subdistrict_district_active_name", "district_code", "is_active", "name"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lgd_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    district_code: Mapped[str] = mapped_column(
        ForeignKey("districts.lgd_code", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(180), index=True)
    local_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_version: Mapped[str] = mapped_column(String(100))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Village(TimestampMixin, Base):
    __tablename__ = "villages"
    __table_args__ = (
        Index("ix_village_subdistrict_active_name", "subdistrict_code", "is_active", "name"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lgd_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    subdistrict_code: Mapped[str] = mapped_column(
        ForeignKey("subdistricts.lgd_code", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(180), index=True)
    local_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_version: Mapped[str] = mapped_column(String(100))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UrbanLocalBody(TimestampMixin, Base):
    __tablename__ = "urban_local_bodies"
    __table_args__ = (
        Index("ix_ulb_state_district_active", "state_code", "district_code", "is_active"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lgd_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    state_code: Mapped[str] = mapped_column(
        ForeignKey("states.lgd_code", ondelete="RESTRICT"), index=True
    )
    district_code: Mapped[str | None] = mapped_column(
        ForeignKey("districts.lgd_code", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(180), index=True)
    local_body_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    local_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_version: Mapped[str] = mapped_column(String(100))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Ward(TimestampMixin, Base):
    __tablename__ = "wards"
    __table_args__ = (
        Index("ix_ward_ulb_active_name", "urban_local_body_code", "is_active", "name"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lgd_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    urban_local_body_code: Mapped[str] = mapped_column(
        ForeignKey("urban_local_bodies.lgd_code", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(180), index=True)
    local_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_version: Mapped[str] = mapped_column(String(100))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LocationImportJob(Base):
    __tablename__ = "location_import_jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    source_url: Mapped[str] = mapped_column(String(500))
    source_version: Mapped[str] = mapped_column(String(100), index=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    source_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    rows_received: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RescuerDocument(Base):
    __tablename__ = "rescuer_documents"
    __table_args__ = (CheckConstraint("file_size > 0", name="ck_rescuer_document_file_size"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescuer_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(80))
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RescuerVerificationHistory(TimestampMixin, Base):
    __tablename__ = "rescuer_verification_history"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescuer_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40), index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AvailabilityHistory(TimestampMixin, Base):
    __tablename__ = "availability_history"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescuer_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="CASCADE"), index=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), index=True)


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "idempotency_key_hash", name="uq_booking_customer_idempotency"
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_booking_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_booking_longitude",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_booking_coordinate_pair",
        ),
        CheckConstraint(
            "(arrival_latitude IS NULL AND arrival_longitude IS NULL) OR "
            "(arrival_latitude IS NOT NULL AND arrival_longitude IS NOT NULL)",
            name="ck_booking_arrival_coordinate_pair",
        ),
        CheckConstraint(
            "arrival_latitude IS NULL OR (arrival_latitude >= -90 AND arrival_latitude <= 90)",
            name="ck_booking_arrival_latitude",
        ),
        CheckConstraint(
            "arrival_longitude IS NULL OR (arrival_longitude >= -180 AND arrival_longitude <= 180)",
            name="ck_booking_arrival_longitude",
        ),
        CheckConstraint(
            "arrival_accuracy IS NULL OR (arrival_accuracy >= 0 AND arrival_accuracy <= 10000)",
            name="ck_booking_arrival_accuracy",
        ),
        Index("ix_booking_customer_created", "customer_id", "created_at"),
        Index("ix_booking_rescuer_status_created", "rescuer_id", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    rescuer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"), index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("villages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    state_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    district_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    subdistrict_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    village_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manual_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    customer_notes: Mapped[str] = mapped_column(Text)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.REQUESTED, index=True
    )
    quoted_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    commission_rate_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.00")
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.DISABLED
    )
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    arrival_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    arrival_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    arrival_review_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BookingEvent(TimestampMixin, Base):
    __tablename__ = "booking_events"
    __table_args__ = (
        UniqueConstraint("booking_id", "sequence", name="uq_booking_event_sequence"),
        Index("ix_booking_event_booking_sequence", "booking_id", "sequence"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(String(500))
    sequence: Mapped[int] = mapped_column(Integer, default=1)


class BookingStatusHistory(TimestampMixin, Base):
    __tablename__ = "booking_status_history"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class NotificationTemplate(TimestampMixin, Base):
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("template_key", "channel", name="uq_notification_template_channel"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_key: Mapped[str] = mapped_column(String(100), index=True)
    channel: Mapped[str] = mapped_column(String(30))
    subject_template: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body_template: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class NotificationEvent(TimestampMixin, Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint("deduplication_key", name="uq_notification_event_deduplication"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(String(500))
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deduplication_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationDeliveryAttempt(TimestampMixin, Base):
    __tablename__ = "notification_delivery_attempts"
    __table_args__ = (
        UniqueConstraint(
            "notification_event_id", "channel", name="uq_notification_delivery_channel"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notification_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notification_events.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(30), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), index=True)
    sanitized_result: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class NotificationPreference(TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_notification_preference_channel"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(30))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    opted_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceRegistration(TimestampMixin, Base):
    __tablename__ = "device_registrations"
    __table_args__ = (
        UniqueConstraint("user_id", "token_hash", name="uq_device_user_token"),
        Index("ix_device_user_active", "user_id", "is_active"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64))
    token_value: Mapped[str] = mapped_column(Text)
    device_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrackingSession(TimestampMixin, Base):
    __tablename__ = "tracking_sessions"
    __table_args__ = (
        Index("ix_tracking_booking_status", "booking_id", "status"),
        Index("ix_tracking_rescuer_status", "rescuer_id", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    rescuer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[TrackingStatus] = mapped_column(
        Enum(TrackingStatus), default=TrackingStatus.ACTIVE, index=True
    )
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_location_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TrackingLocation(TimestampMixin, Base):
    __tablename__ = "tracking_locations"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_tracking_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_tracking_longitude"),
        CheckConstraint("accuracy >= 0 AND accuracy <= 10000", name="ck_tracking_accuracy"),
        Index("ix_tracking_location_session_recorded", "tracking_session_id", "recorded_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tracking_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tracking_sessions.id", ondelete="CASCADE"), index=True
    )
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class ServicePricingRule(TimestampMixin, Base):
    __tablename__ = "service_pricing_rules"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    state_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    legally_authorized: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class CommissionRule(TimestampMixin, Base):
    __tablename__ = "commission_rules"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    legally_authorized: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class BookingFinancialSnapshot(TimestampMixin, Base):
    __tablename__ = "booking_financial_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, index=True
    )
    service_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    rescuer_share: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    pricing_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_illustrative: Mapped[bool] = mapped_column(Boolean, default=True)


class RescueOutcome(TimestampMixin, Base):
    __tablename__ = "rescue_outcomes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class RescueSession(TimestampMixin, Base):
    __tablename__ = "rescue_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, index=True
    )
    rescuer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"), index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="IN_PROGRESS", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RescueReport(TimestampMixin, Base):
    __tablename__ = "rescue_reports"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_rescue_report_booking"),
        UniqueConstraint(
            "rescuer_id", "idempotency_key_hash", name="uq_rescue_report_rescuer_idempotency"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescue_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescue_sessions.id", ondelete="CASCADE"), unique=True, index=True
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    rescuer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"), index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    outcome_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescue_outcomes.id", ondelete="RESTRICT"), index=True
    )
    observations: Mapped[str] = mapped_column(Text)
    authorized_action_summary: Mapped[str] = mapped_column(Text)
    referral_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    species_text: Mapped[str | None] = mapped_column(String(160), nullable=True)
    species_verification: Mapped[str] = mapped_column(String(40), default="UNVERIFIED", index=True)
    completion_status: Mapped[str] = mapped_column(String(40), default="SUBMITTED", index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key_hash: Mapped[str] = mapped_column(String(64))
    idempotency_request_hash: Mapped[str] = mapped_column(String(64))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RescueReportEvent(TimestampMixin, Base):
    __tablename__ = "rescue_report_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescue_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescue_reports.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(String(500))


class RescueMedia(TimestampMixin, Base):
    __tablename__ = "rescue_media"
    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_rescue_media_file_size"),
        Index("ix_rescue_media_booking_type", "booking_id", "evidence_type"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    rescue_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescue_sessions.id", ondelete="CASCADE"), index=True
    )
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(80))
    file_size: Mapped[int] = mapped_column(Integer)
    evidence_type: Mapped[str] = mapped_column(String(50), index=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    malware_scan_status: Mapped[str] = mapped_column(
        String(30), default="NOT_CONFIGURED", index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class EvidenceLocationMetadata(TimestampMixin, Base):
    __tablename__ = "evidence_location_metadata"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_evidence_location_latitude"),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_evidence_location_longitude"
        ),
        CheckConstraint(
            "accuracy >= 0 AND accuracy <= 10000", name="ck_evidence_location_accuracy"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescue_media_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescue_media.id", ondelete="CASCADE"), unique=True, index=True
    )
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float] = mapped_column(Float)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    association_only: Mapped[bool] = mapped_column(Boolean, default=True)


class EvidenceAuditEvent(TimestampMixin, Base):
    __tablename__ = "evidence_audit_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescue_media_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescue_media.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(String(500))


class CompletionDispute(TimestampMixin, Base):
    __tablename__ = "completion_disputes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(40), default="OPEN", index=True)
    coordinator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "idempotency_key_hash", name="uq_payment_customer_idempotency"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payment_reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    method: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64))
    idempotency_request_hash: Mapped[str] = mapped_column(String(64))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PaymentAttempt(TimestampMixin, Base):
    __tablename__ = "payment_attempts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    sanitized_result: Mapped[str] = mapped_column(String(500))


class PaymentEvent(TimestampMixin, Base):
    __tablename__ = "payment_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(String(500))


class PaymentRefund(TimestampMixin, Base):
    __tablename__ = "payment_refunds"
    __table_args__ = (
        UniqueConstraint(
            "payment_id", "idempotency_key_hash", name="uq_refund_payment_idempotency"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="DEMO_REFUNDED", index=True)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class PaymentProviderWebhook(TimestampMixin, Base):
    __tablename__ = "payment_provider_webhooks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    event_reference: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    sanitized_status: Mapped[str] = mapped_column(String(80))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class CommissionEntry(TimestampMixin, Base):
    __tablename__ = "commission_entries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), unique=True, index=True
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), index=True
    )
    rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    eligible_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rescuer_share: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reversed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(40), default="DEMO_RECORDED", index=True)
    settlement_status: Mapped[str] = mapped_column(String(40), default="NOT_SETTLED", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class SettlementAccount(TimestampMixin, Base):
    __tablename__ = "settlement_accounts"
    __table_args__ = (
        UniqueConstraint("rescuer_id", "currency", name="uq_settlement_rescuer_currency"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rescuer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"), index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(40), default="DEMO_ONLY", index=True)
    withdrawable: Mapped[bool] = mapped_column(Boolean, default=False)


class SettlementEntry(TimestampMixin, Base):
    __tablename__ = "settlement_entries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    settlement_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("settlement_accounts.id", ondelete="RESTRICT"), index=True
    )
    commission_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commission_entries.id", ondelete="RESTRICT"), unique=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(40), default="PENDING_DEMO", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class FinancialLedgerEntry(TimestampMixin, Base):
    __tablename__ = "financial_ledger_entries"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_financial_ledger_amount"),
        CheckConstraint(
            "direction IN ('DEBIT', 'CREDIT')",
            name="ck_financial_ledger_direction",
        ),
        Index("ix_ledger_transaction_group", "transaction_group", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_group: Mapped[str] = mapped_column(String(64), index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), index=True
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), index=True
    )
    account_code: Mapped[str] = mapped_column(String(60), index=True)
    direction: Mapped[str] = mapped_column(String(10), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    description: Mapped[str] = mapped_column(String(300))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_review_booking"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    rescuer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rescuer_profiles.id", ondelete="RESTRICT"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    review_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(40), default="PUBLISHED_DEMO", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReviewAbuseReport(TimestampMixin, Base):
    __tablename__ = "review_abuse_reports"
    __table_args__ = (UniqueConstraint("review_id", "reporter_id", name="uq_review_reporter"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="OPEN", index=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
