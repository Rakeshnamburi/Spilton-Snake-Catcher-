from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.entities import TrackingStatus
from app.schemas.marketplace import BookingEventResponse


class DeviceRegister(BaseModel):
    platform: Literal["ANDROID", "IOS", "WEB"]
    token: str = Field(min_length=20, max_length=4096)
    device_label: str | None = Field(default=None, max_length=100)

    @field_validator("token", "device_label")
    @classmethod
    def clean(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class DeviceResponse(BaseModel):
    id: UUID
    platform: str
    device_label: str | None
    token_hint: str
    is_active: bool
    last_seen_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    channel: Literal["EMAIL", "SMS", "WHATSAPP", "PUSH"]
    enabled: bool
    explicit_opt_in: bool = False


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    channel: str
    is_enabled: bool
    opted_in_at: datetime | None


class TrackingConsent(BaseModel):
    consent: Literal[True]
    disclosure_version: Literal["day4-demo-v1"]


class TrackingLocationCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(ge=0, le=10000)
    recorded_at: datetime
    is_simulated: Literal[True]


class TrackingLocationResponse(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    accuracy: float
    recorded_at: datetime
    received_at: datetime
    is_simulated: bool


class RouteResponse(BaseModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    provider: str | None
    road_distance_km: float | None
    geographic_distance_km: float | None
    duration_seconds: int | None
    eta_at: datetime | None
    coordinates: list[list[float]] = Field(default_factory=list)
    is_demo: bool = True
    message: str


class TrackingResponse(BaseModel):
    session_id: UUID | None
    booking_id: UUID
    status: TrackingStatus | None
    consent_timestamp: datetime | None
    started_at: datetime | None
    paused_at: datetime | None
    stopped_at: datetime | None
    expires_at: datetime | None
    last_location_at: datetime | None
    latest_location: TrackingLocationResponse | None
    destination_latitude: float | None
    destination_longitude: float | None
    destination_precision: str
    route: RouteResponse
    is_demo: bool = True
    live_dispatch_enabled: bool = False


class BookingEventPage(BaseModel):
    items: list[BookingEventResponse]
    last_sequence: int
    heartbeat_seconds: int = 15


class DeliveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    notification_event_id: UUID
    channel: str
    provider: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    delivered_at: datetime | None
    sanitized_result: str | None
    created_at: datetime
