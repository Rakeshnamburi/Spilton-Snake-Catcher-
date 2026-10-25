from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.regions import TARGET_STATES, coordinates_are_in_state
from app.models.entities import IncidentStatus, Role, Urgency


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    password: str = Field(min_length=10, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) < 2:
            raise ValueError("Name must contain at least 2 non-whitespace characters")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email: EmailStr
    phone: str | None = None
    role: Role


class OtpRequestBody(BaseModel):
    email: EmailStr


class OtpVerifyBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)
    # Optional profile details used only when this OTP creates a brand new account.
    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")


class OAuthExchangeBody(BaseModel):
    code: str = Field(min_length=8, max_length=512)


class AuthProvidersResponse(BaseModel):
    password: bool = True
    email_otp: bool = True
    google: bool = False
    microsoft: bool = False


class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str | None = None
    token_type: str = "bearer"
    csrf_token: str | None = None


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    current_password: str = Field(min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_profile_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) < 2:
            raise ValueError("Name must contain at least 2 non-whitespace characters")
        return cleaned


class AccountDataRequestCreate(BaseModel):
    request_type: Literal["EXPORT", "DELETION"]
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split()) or None


class AccountDataRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_type: str
    status: str
    reason: str | None
    processed_at: datetime | None
    created_at: datetime


class IncidentCreate(BaseModel):
    reporter_name: str = Field(min_length=2, max_length=120)
    contact_phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    reporter_email: EmailStr | None = None
    state: str
    district: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=120)
    landmark: str | None = Field(default=None, max_length=200)
    address_description: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0, le=10000)
    sighting_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = Field(min_length=10, max_length=2000)
    injury_reported: bool = False
    snake_visible: bool = False
    immediate_danger: bool = False
    urgency: Urgency = Urgency.STANDARD
    consent: bool

    @field_validator("state")
    @classmethod
    def supported_state(cls, value: str) -> str:
        value = value.strip()
        if value not in TARGET_STATES:
            raise ValueError("State is outside the current five-state demo scope")
        return value

    @field_validator("reporter_name", "district", "city", "description")
    @classmethod
    def clean_required_text(cls, value: str, info: ValidationInfo) -> str:
        if any(ord(character) < 32 and not character.isspace() for character in value):
            raise ValueError("Control characters are not allowed")
        cleaned = " ".join(value.strip().split())
        minimum = 10 if info.field_name == "description" else 2
        if len(cleaned) < minimum:
            raise ValueError(
                f"{info.field_name.replace('_', ' ').title()} must contain at least "
                f"{minimum} non-whitespace characters"
            )
        return cleaned

    @field_validator("landmark", "address_description")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(ord(character) < 32 and not character.isspace() for character in value):
            raise ValueError("Control characters are not allowed")
        return " ".join(value.strip().split()) or None

    @field_validator("sighting_at")
    @classmethod
    def reasonable_sighting_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Sighting time cannot be in the future")
        return value

    @field_validator("consent")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent acknowledgement is required")
        return value

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        if self.location_accuracy is not None and self.latitude is None:
            raise ValueError("Location accuracy requires GPS coordinates")
        if (
            self.latitude is not None
            and self.longitude is not None
            and not coordinates_are_in_state(self.state, self.latitude, self.longitude)
        ):
            raise ValueError("Coordinates appear outside the selected state")
        return self


class IncidentMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    incident_id: UUID
    original_filename: str
    content_type: str
    file_size: int
    uploaded_at: datetime

    @computed_field
    @property
    def download_url(self) -> str:
        return f"/api/v1/incidents/{self.incident_id}/media/{self.id}"


class IncidentResponse(BaseModel):
    """Authorized incident view; reporter contact details are deliberately omitted."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reference_code: str
    reporter_name: str
    state: str
    district: str
    city: str
    landmark: str | None
    address_description: str | None
    latitude: float | None
    longitude: float | None
    location_accuracy: float | None
    sighting_at: datetime
    description: str
    injury_reported: bool
    snake_visible: bool
    immediate_danger: bool
    urgency: Urgency
    status: IncidentStatus
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    media: list[IncidentMediaResponse] = Field(default_factory=list)


class IncidentListItem(BaseModel):
    """Minimum data needed by a citizen's report list."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reference_code: str
    state: str
    district: str
    city: str
    urgency: Urgency
    status: IncidentStatus
    is_demo: bool
    sighting_at: datetime
    created_at: datetime


class IncidentPage(BaseModel):
    items: list[IncidentListItem]
    total: int
    page: int
    page_size: int
    pages: int


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    details: str
    created_at: datetime


class AdminIncidentListItem(IncidentListItem):
    injury_reported: bool
    immediate_danger: bool


class AdminIncidentPage(BaseModel):
    items: list[AdminIncidentListItem]
    total: int
    page: int
    page_size: int
    pages: int


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split()) or None


class EmergencyContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_name: str
    state: str
    district: str | None
    phone: str
    source_url: str
    verified_at: datetime
