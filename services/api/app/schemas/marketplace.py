from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.entities import AvailabilityStatus, BookingStatus, VerificationStatus


class LocationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lgd_code: str
    name: str
    local_name: str | None
    is_active: bool
    source_version: str


class LocationPage(BaseModel):
    items: list[LocationItem]
    total: int
    page: int
    limit: int
    pages: int


class LocationSearchItem(LocationItem):
    entity_type: str
    parent_code: str | None = None


class RescuerApplicationCreate(BaseModel):
    public_display_name: str = Field(min_length=2, max_length=120)
    state_code: str = Field(min_length=1, max_length=20)
    district_code: str = Field(min_length=1, max_length=20)
    subdistrict_code: str | None = Field(default=None, max_length=20)
    village_code: str | None = Field(default=None, max_length=20)
    organization_id: UUID | None = None
    organization_name: str = Field(min_length=2, max_length=180)
    years_experience: int = Field(ge=0, le=80)
    languages: list[str] = Field(min_length=1, max_length=12)
    training_details: str = Field(min_length=10, max_length=2000)
    authorization_reference: str = Field(min_length=3, max_length=160)
    issuing_authority: str = Field(min_length=3, max_length=180)
    authorization_issue_date: date
    authorization_expiry: date
    service_area_description: str = Field(min_length=5, max_length=500)
    service_radius_km: float = Field(gt=0, le=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    operating_hours: dict[str, str] = Field(default_factory=dict)
    acknowledgement: bool

    @field_validator(
        "public_display_name",
        "organization_name",
        "training_details",
        "authorization_reference",
        "issuing_authority",
        "service_area_description",
    )
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("languages")
    @classmethod
    def clean_languages(cls, values: list[str]) -> list[str]:
        cleaned = list(
            dict.fromkeys(" ".join(value.strip().split()) for value in values if value.strip())
        )
        if not cleaned:
            raise ValueError("At least one spoken language is required")
        if any(len(value) > 60 for value in cleaned):
            raise ValueError("Language labels must be 60 characters or shorter")
        return cleaned

    @model_validator(mode="after")
    def validate_application(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        if self.authorization_expiry <= self.authorization_issue_date:
            raise ValueError("Authorization expiry must be after its issue date")
        if not self.acknowledgement:
            raise ValueError("The legal authorization acknowledgement is required")
        return self


class RescuerApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    organization_id: UUID | None
    public_display_name: str | None
    state_code: str | None
    district_code: str | None
    subdistrict_code: str | None
    village_code: str | None
    organization_name: str | None
    years_experience: int
    languages: list[str]
    training_details: str | None
    authorization_reference: str | None
    issuing_authority: str | None
    authorization_issue_date: date | None
    authorization_expiry: date | None
    service_area_description: str
    service_radius_km: float
    availability: AvailabilityStatus
    operating_hours: dict
    verification_status: VerificationStatus
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class PublicRescuer(BaseModel):
    id: UUID
    display_name: str
    organization: str
    years_experience: int
    languages: list[str]
    service_area: str
    availability: AvailabilityStatus
    verification_status: VerificationStatus
    authorization_expiry: date | None
    average_rating: Decimal
    review_count: int
    completed_service_count: int
    distance_km: float | None = None
    is_demo: bool = True
    pricing_enabled: bool = False
    service_charge: Decimal | None = None
    currency: str = "INR"


class RescuerPage(BaseModel):
    items: list[PublicRescuer]
    total: int
    page: int
    limit: int
    pages: int


class AvailabilityUpdate(BaseModel):
    status: AvailabilityStatus
    operating_hours: dict[str, str] | None = None


class VerificationUpdate(BaseModel):
    status: VerificationStatus
    organization_id: UUID | None = None
    note: str = Field(min_length=3, max_length=500)

    @field_validator("status")
    @classmethod
    def supported_status(cls, value: VerificationStatus) -> VerificationStatus:
        if value not in {
            VerificationStatus.UNDER_REVIEW,
            VerificationStatus.VERIFIED,
            VerificationStatus.REJECTED,
            VerificationStatus.SUSPENDED,
            VerificationStatus.EXPIRED,
        }:
            raise ValueError("Unsupported verification transition")
        return value


class BookingCreate(BaseModel):
    rescuer_id: UUID
    incident_id: UUID | None = None
    state_code: str = Field(min_length=1, max_length=20)
    district_code: str | None = Field(default=None, max_length=20)
    subdistrict_code: str | None = Field(default=None, max_length=20)
    village_code: str | None = Field(default=None, max_length=20)
    manual_address: str | None = Field(default=None, max_length=500)
    landmark: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0, le=10000)
    customer_notes: str = Field(min_length=10, max_length=2000)
    confirm_demo_and_safety: bool

    @field_validator("manual_address", "landmark", "customer_notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split()) or None

    @model_validator(mode="after")
    def validate_location(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        if self.location_accuracy is not None and self.latitude is None:
            raise ValueError("Location accuracy requires coordinates")
        if not self.manual_address and not self.village_code and self.latitude is None:
            raise ValueError("Confirm a directory location, manual address, or coordinates")
        if not self.confirm_demo_and_safety:
            raise ValueError("Demo and safety acknowledgement is required")
        return self


class BookingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    details: str
    sequence: int
    created_at: datetime


class BookingHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    previous_status: str | None
    status: str
    note: str | None
    created_at: datetime


class BookingResponse(BaseModel):
    id: UUID
    booking_reference: str
    customer_id: UUID
    rescuer_id: UUID
    rescuer_display_name: str
    organization: str
    incident_id: UUID | None
    state_code: str | None
    district_code: str | None
    subdistrict_code: str | None
    village_code: str | None
    manual_address: str | None
    landmark: str | None
    latitude: float | None
    longitude: float | None
    location_accuracy: float | None
    location_precision: str
    customer_notes: str
    status: BookingStatus
    quoted_amount: Decimal | None
    currency: str
    commission_rate_snapshot: Decimal
    payment_status: str
    is_demo: bool
    pricing_enabled: bool = False
    live_dispatch_enabled: bool = False
    accepted_at: datetime | None
    responded_at: datetime | None
    arrived_at: datetime | None
    arrival_accuracy: float | None
    arrival_review_warning: bool
    completed_at: datetime | None
    customer_confirmed_at: datetime | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    events: list[BookingEventResponse] = Field(default_factory=list)
    history: list[BookingHistoryResponse] = Field(default_factory=list)


class BookingPage(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    limit: int
    pages: int


class BookingAction(BaseModel):
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        return " ".join(value.strip().split()) if value and value.strip() else None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    title: str
    body: str
    booking_id: UUID | None
    deep_link: str | None
    is_demo: bool
    read_at: datetime | None
    created_at: datetime
