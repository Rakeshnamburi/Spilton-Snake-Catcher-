from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArrivalCreate(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=10_000)
    location_consent: bool = False

    @model_validator(mode="after")
    def validate_location(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        if self.latitude is not None and not self.location_consent:
            raise ValueError("Explicit location consent is required")
        if self.accuracy is not None and self.latitude is None:
            raise ValueError("Accuracy requires coordinates")
        return self


class RescueOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    label: str
    description: str


class RescueSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    status: str
    started_at: datetime
    ended_at: datetime | None
    is_demo: bool


class RescueReportCreate(BaseModel):
    outcome_code: str = Field(min_length=3, max_length=60, pattern=r"^[A-Z0-9_]+$")
    observations: str = Field(min_length=5, max_length=4000)
    authorized_action_summary: str = Field(min_length=5, max_length=4000)
    referral_details: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    species_text: str | None = Field(default=None, max_length=160)
    confirm_demo: bool

    @model_validator(mode="after")
    def validate_demo_confirmation(self):
        if not self.confirm_demo:
            raise ValueError("Demo completion acknowledgement is required")
        return self


class RescueReportResponse(BaseModel):
    id: UUID
    booking_id: UUID
    rescue_session_id: UUID
    outcome_code: str
    outcome_label: str
    observations: str
    authorized_action_summary: str
    referral_details: str | None
    notes: str | None
    species_text: str | None
    species_verification: str
    completion_status: str
    completed_at: datetime
    is_demo: bool


class EvidenceResponse(BaseModel):
    id: UUID
    booking_id: UUID
    original_filename: str
    content_type: str
    file_size: int
    evidence_type: str
    captured_at: datetime | None
    location_attached: bool
    retention_expires_at: datetime
    created_at: datetime
    is_demo: bool


class CompletionConfirmResponse(BaseModel):
    booking_id: UUID
    status: str
    completion_status: str
    customer_confirmed_at: datetime
    is_demo: bool


class DisputeCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class DisputeResolution(BaseModel):
    resolution_note: str = Field(min_length=5, max_length=1000)
    restore_completed: bool = True


class DisputeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    customer_id: UUID
    reason: str
    status: str
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime
    is_demo: bool


PaymentMethod = Literal["DEMO_ONLINE", "DEMO_CASH", "NO_CHARGE"]


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(ge=Decimal("0.00"), le=Decimal("100000.00"))
    currency: Literal["INR"] = "INR"
    confirm_demo: bool

    @model_validator(mode="after")
    def validate_method_amount(self):
        if not self.confirm_demo:
            raise ValueError("Demo payment acknowledgement is required")
        if self.method == "NO_CHARGE" and self.amount != Decimal("0"):
            raise ValueError("NO_CHARGE must use an amount of 0")
        if self.method != "NO_CHARGE" and self.amount <= Decimal("0"):
            raise ValueError("Demo cash and online payments require a positive amount")
        return self


class PaymentConfirm(BaseModel):
    simulate_failure: bool = False


class CashConfirm(BaseModel):
    confirm_received: bool


class RefundCreate(BaseModel):
    amount: Decimal = Field(gt=Decimal("0.00"), le=Decimal("100000.00"))
    reason: str = Field(min_length=5, max_length=500)


class PaymentResponse(BaseModel):
    id: UUID
    payment_reference: str
    booking_id: UUID
    amount: Decimal
    currency: str
    method: str
    status: str
    confirmed_at: datetime | None
    refunded_amount: Decimal
    commission_rate: Decimal | None = None
    commission_amount: Decimal | None = None
    rescuer_share: Decimal | None = None
    is_demo: bool
    created_at: datetime


class EarningsResponse(BaseModel):
    rescuer_id: UUID
    currency: str
    gross_demo_amount: Decimal
    commission_demo_amount: Decimal
    rescuer_demo_share: Decimal
    reversed_demo_amount: Decimal
    withdrawable: bool = False
    disclaimer: str


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=1000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_change(self):
        if self.rating is None and self.review_text is None:
            raise ValueError("Provide a rating or review text to update")
        return self


class ReviewReportCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class ReviewModeration(BaseModel):
    status: Literal["PUBLISHED_DEMO", "HIDDEN", "REMOVED"]
    resolution_note: str | None = Field(default=None, max_length=500)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    customer_id: UUID
    rescuer_id: UUID
    rating: int
    review_text: str | None
    moderation_status: str
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class PublicReviewResponse(BaseModel):
    id: UUID
    rating: int
    review_text: str | None
    created_at: datetime
    is_demo: bool


class ReviewSummary(BaseModel):
    rescuer_id: UUID
    average_rating: Decimal
    review_count: int
    distribution: dict[int, int]
    is_demo: bool = True
