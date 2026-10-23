from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.bookings import _owned_booking
from app.api.deps import get_current_user, require_roles
from app.api.marketplace_helpers import fail, get_profile_for_user, utcnow
from app.core.config import get_settings
from app.core.security import keyed_digest
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    Booking,
    BookingStatus,
    CommissionEntry,
    FinancialLedgerEntry,
    Payment,
    PaymentAttempt,
    PaymentEvent,
    PaymentProviderWebhook,
    PaymentRefund,
    PaymentStatus,
    RescuerProfile,
    Role,
    User,
)
from app.schemas.day5 import (
    CashConfirm,
    EarningsResponse,
    PaymentConfirm,
    PaymentCreate,
    PaymentResponse,
    RefundCreate,
)
from app.services.day5_finance import (
    money,
    record_demo_payment_accounting,
    record_demo_refund_accounting,
)
from app.services.marketplace import create_in_app_notification
from app.services.payment_gateway import get_payment_gateway
from app.services.rate_limit import rate_limiter

router = APIRouter(tags=["day5-payments"])


def _validated_idempotency_key(key: str | None) -> str:
    if not key:
        raise fail(400, "IDEMPOTENCY_KEY_REQUIRED", "An Idempotency-Key header is required")
    cleaned = key.strip()
    if not 8 <= len(cleaned) <= 128 or any(ord(character) < 33 for character in cleaned):
        raise fail(400, "INVALID_IDEMPOTENCY_KEY", "Use an 8–128 character idempotency key")
    return cleaned


def _payment_response(db: Session, payment: Payment) -> PaymentResponse:
    commission = db.scalar(select(CommissionEntry).where(CommissionEntry.payment_id == payment.id))
    return PaymentResponse(
        id=payment.id,
        payment_reference=payment.payment_reference,
        booking_id=payment.booking_id,
        amount=money(payment.amount),
        currency=payment.currency,
        method=payment.method,
        status=payment.status,
        confirmed_at=payment.confirmed_at,
        refunded_amount=money(payment.refunded_amount or 0),
        commission_rate=commission.rate_snapshot if commission else None,
        commission_amount=commission.commission_amount if commission else None,
        rescuer_share=commission.rescuer_share if commission else None,
        is_demo=payment.is_demo,
        created_at=payment.created_at,
    )


def _payment_access(db: Session, payment_id: UUID, user: User, *, lock=False) -> Payment:
    statement = select(Payment).where(Payment.id == payment_id)
    if lock:
        statement = statement.with_for_update()
    payment = db.scalar(statement)
    if payment is None:
        raise fail(404, "PAYMENT_NOT_FOUND", "Payment not found")
    booking = db.get(Booking, payment.booking_id)
    profile = get_profile_for_user(db, user.id)
    if (
        payment.customer_id != user.id
        and (profile is None or booking.rescuer_id != profile.id)
        and user.role not in {Role.COORDINATOR, Role.ADMIN}
    ):
        raise fail(403, "PAYMENT_ACCESS_DENIED", "You cannot access this demo payment")
    return payment


def _record_success(
    db: Session,
    *,
    payment: Payment,
    booking: Booking,
    actor: User,
) -> None:
    if payment.status == "DEMO_SUCCEEDED":
        return
    profile = db.get(RescuerProfile, booking.rescuer_id)
    payment.status = "DEMO_SUCCEEDED"
    payment.confirmed_at = utcnow()
    booking.payment_status = PaymentStatus.PAID
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            actor_id=actor.id,
            event_type="DEMO_PAYMENT_SUCCEEDED",
            details="A simulated payment succeeded; no real funds moved.",
        )
    )
    record_demo_payment_accounting(
        db,
        payment=payment,
        booking=booking,
        profile=profile,
    )
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type="DEMO_PAYMENT_SUCCEEDED",
        title="Demo payment recorded",
        body=f"Illustrative payment for {booking.booking_reference} was recorded.",
    )
    if profile is not None:
        create_in_app_notification(
            db,
            recipient_id=profile.user_id,
            booking_id=booking.id,
            event_type="DEMO_PAYMENT_SUCCEEDED",
            title="Demo payment recorded",
            body=f"Illustrative payment for {booking.booking_reference} was recorded.",
        )


@router.post(
    "/bookings/{booking_id}/payments",
    response_model=PaymentResponse,
    status_code=201,
)
def create_payment(
    booking_id: UUID,
    payload: PaymentCreate,
    request: Request,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.demo_mode or settings.payments_enabled:
        raise fail(503, "DEMO_PAYMENT_MODE_REQUIRED", "Only simulated payments are enabled")
    retry = rate_limiter.check(
        f"payment-create:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=10,
        window_seconds=3600,
    )
    if retry is not None:
        raise fail(429, "PAYMENT_RATE_LIMITED", "Too many payment attempts")
    key = _validated_idempotency_key(idempotency_key)
    key_hash = keyed_digest(f"payment:{user.id}:{key}")
    request_hash = hashlib.sha256(
        json.dumps(
            payload.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    existing = db.scalar(
        select(Payment).where(
            Payment.customer_id == user.id,
            Payment.idempotency_key_hash == key_hash,
        )
    )
    if existing is not None:
        if existing.idempotency_request_hash != request_hash:
            raise fail(
                409,
                "IDEMPOTENCY_CONFLICT",
                "This key was already used for a different demo payment",
            )
        response.headers["X-Idempotent-Replay"] = "true"
        return _payment_response(db, existing)

    booking = _owned_booking(db, booking_id, user, lock=True)
    if booking.customer_id != user.id:
        raise fail(403, "CUSTOMER_REQUIRED", "Only the booking customer can pay")
    if booking.status != BookingStatus.COMPLETED:
        raise fail(409, "COMPLETION_REQUIRED", "Complete the demo booking before payment")
    active = db.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id,
            Payment.status.in_(
                {
                    "DEMO_PENDING",
                    "CASH_AWAITING_CONFIRMATION",
                    "DEMO_SUCCEEDED",
                    "NO_CHARGE",
                    "DEMO_PARTIALLY_REFUNDED",
                }
            ),
        )
    )
    if active is not None:
        raise fail(409, "PAYMENT_ALREADY_EXISTS", "A demo payment already exists")

    initial_status = {
        "DEMO_ONLINE": "DEMO_PENDING",
        "DEMO_CASH": "CASH_AWAITING_CONFIRMATION",
        "NO_CHARGE": "NO_CHARGE",
    }[payload.method]
    payment = Payment(
        payment_reference=f"PAY-DEMO-{secrets.token_hex(6).upper()}",
        booking_id=booking.id,
        customer_id=user.id,
        amount=money(payload.amount),
        currency=payload.currency,
        method=payload.method,
        status=initial_status,
        idempotency_key_hash=key_hash,
        idempotency_request_hash=request_hash,
        refunded_amount=Decimal("0.00"),
        is_demo=True,
    )
    db.add(payment)
    db.flush()
    db.add(
        PaymentAttempt(
            payment_id=payment.id,
            status=initial_status,
            attempt_number=1,
            sanitized_result="Demo method selected; no financial credentials collected.",
        )
    )
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            actor_id=user.id,
            event_type="DEMO_PAYMENT_CREATED",
            details="A simulated payment record was created.",
        )
    )
    if payload.method == "NO_CHARGE":
        payment.confirmed_at = utcnow()
        booking.payment_status = PaymentStatus.NOT_REQUIRED
    else:
        booking.payment_status = PaymentStatus.PENDING
    db.add(
        AuditLog(
            actor_id=user.id,
            action="payment.create.demo",
            entity_type="payment",
            entity_id=str(payment.id),
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        replay = db.scalar(
            select(Payment).where(
                Payment.customer_id == user.id,
                Payment.idempotency_key_hash == key_hash,
            )
        )
        if replay and replay.idempotency_request_hash == request_hash:
            response.headers["X-Idempotent-Replay"] = "true"
            return _payment_response(db, replay)
        raise fail(409, "PAYMENT_CONFLICT", "Demo payment could not be created safely") from error
    db.refresh(payment)
    return _payment_response(db, payment)


@router.post("/payments/{payment_id}/confirm", response_model=PaymentResponse)
def confirm_demo_online(
    payment_id: UUID,
    payload: PaymentConfirm,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payment = _payment_access(db, payment_id, user, lock=True)
    if payment.customer_id != user.id:
        raise fail(403, "CUSTOMER_REQUIRED", "Only the customer can run this simulation")
    if payment.method != "DEMO_ONLINE" or payment.status != "DEMO_PENDING":
        raise fail(409, "PAYMENT_NOT_CONFIRMABLE", "This demo payment cannot be confirmed")
    booking = db.get(Booking, payment.booking_id)
    attempt_number = (
        db.scalar(
            select(func.count())
            .select_from(PaymentAttempt)
            .where(PaymentAttempt.payment_id == payment.id)
        )
        or 0
    ) + 1
    if payload.simulate_failure:
        payment.status = "DEMO_FAILED"
        booking.payment_status = PaymentStatus.FAILED
        db.add(
            PaymentAttempt(
                payment_id=payment.id,
                status="DEMO_FAILED",
                attempt_number=attempt_number,
                sanitized_result="User-selected demo failure; no provider contacted.",
            )
        )
        db.add(
            PaymentEvent(
                payment_id=payment.id,
                actor_id=user.id,
                event_type="DEMO_PAYMENT_FAILED",
                details="A simulated payment failure was recorded.",
            )
        )
        create_in_app_notification(
            db,
            recipient_id=booking.customer_id,
            booking_id=booking.id,
            event_type="DEMO_PAYMENT_FAILED",
            title="Demo payment simulation failed",
            body=f"The simulation for {booking.booking_reference} failed; no money moved.",
        )
    else:
        gateway_result = get_payment_gateway().authorize(
            amount=payment.amount,
            currency=payment.currency,
            idempotency_key=str(payment.id),
        )
        db.add(
            PaymentAttempt(
                payment_id=payment.id,
                status=gateway_result.status,
                attempt_number=attempt_number,
                sanitized_result=gateway_result.sanitized_message,
            )
        )
        _record_success(db, payment=payment, booking=booking, actor=user)
    db.commit()
    db.refresh(payment)
    return _payment_response(db, payment)


@router.post("/payments/{payment_id}/cash-confirm", response_model=PaymentResponse)
def confirm_demo_cash(
    payment_id: UUID,
    payload: CashConfirm,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payment = _payment_access(db, payment_id, user, lock=True)
    booking = db.get(Booking, payment.booking_id)
    profile = get_profile_for_user(db, user.id)
    if profile is None or profile.id != booking.rescuer_id:
        raise fail(403, "ASSIGNED_RESCUER_REQUIRED", "Only the assigned rescuer can confirm cash")
    if not payload.confirm_received:
        raise fail(422, "CASH_CONFIRMATION_REQUIRED", "Confirm the simulated cash receipt")
    if payment.method != "DEMO_CASH" or payment.status != "CASH_AWAITING_CONFIRMATION":
        raise fail(409, "PAYMENT_NOT_CONFIRMABLE", "This demo cash record cannot be confirmed")
    _record_success(db, payment=payment, booking=booking, actor=user)
    db.commit()
    db.refresh(payment)
    return _payment_response(db, payment)


@router.get("/payments", response_model=list[PaymentResponse])
def my_payments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(Payment).where(Payment.customer_id == user.id).order_by(Payment.created_at.desc())
    ).all()
    return [_payment_response(db, row) for row in rows]


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def payment_detail(
    payment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _payment_response(db, _payment_access(db, payment_id, user))


@router.post("/admin/payments/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: UUID,
    payload: RefundCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    key = _validated_idempotency_key(idempotency_key)
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if payment is None:
        raise fail(404, "PAYMENT_NOT_FOUND", "Payment not found")
    if payment.status not in {"DEMO_SUCCEEDED", "DEMO_PARTIALLY_REFUNDED"}:
        raise fail(409, "PAYMENT_NOT_REFUNDABLE", "Only a successful demo payment can be refunded")
    key_hash = keyed_digest(f"refund:{payment.id}:{key}")
    existing = db.scalar(
        select(PaymentRefund).where(
            PaymentRefund.payment_id == payment.id,
            PaymentRefund.idempotency_key_hash == key_hash,
        )
    )
    if existing is not None:
        if money(existing.amount) != money(payload.amount) or existing.reason != payload.reason:
            raise fail(409, "IDEMPOTENCY_CONFLICT", "This refund key has different details")
        return _payment_response(db, payment)
    remaining = money(payment.amount) - money(payment.refunded_amount or 0)
    if money(payload.amount) > remaining:
        raise fail(422, "REFUND_EXCEEDS_PAYMENT", "Refund exceeds the remaining demo amount")
    commission = db.scalar(
        select(CommissionEntry).where(CommissionEntry.payment_id == payment.id).with_for_update()
    )
    if commission is None:
        raise fail(409, "ACCOUNTING_NOT_FOUND", "Demo accounting entry is missing")
    refund = PaymentRefund(
        payment_id=payment.id,
        amount=money(payload.amount),
        reason=payload.reason,
        status="DEMO_REFUNDED",
        idempotency_key_hash=key_hash,
        is_demo=True,
    )
    db.add(refund)
    record_demo_refund_accounting(
        db,
        payment=payment,
        commission=commission,
        refund_amount=payload.amount,
    )
    payment.refunded_amount = money(payment.refunded_amount or 0) + money(payload.amount)
    payment.status = (
        "DEMO_REFUNDED"
        if money(payment.refunded_amount) >= money(payment.amount)
        else "DEMO_PARTIALLY_REFUNDED"
    )
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            actor_id=admin.id,
            event_type="DEMO_REFUND_RECORDED",
            details="An authorized administrator recorded a simulated refund.",
        )
    )
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="payment.refund.demo",
            entity_type="payment",
            entity_id=str(payment.id),
        )
    )
    db.commit()
    db.refresh(payment)
    return _payment_response(db, payment)


@router.get("/rescuer/earnings", response_model=EarningsResponse)
def rescuer_earnings(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.RESCUER)),
):
    profile = get_profile_for_user(db, user.id)
    if profile is None:
        raise fail(403, "RESCUER_PROFILE_REQUIRED", "Rescuer profile required")
    rows = db.scalars(
        select(CommissionEntry)
        .join(Booking, Booking.id == CommissionEntry.booking_id)
        .where(Booking.rescuer_id == profile.id)
    ).all()
    return EarningsResponse(
        rescuer_id=profile.id,
        currency="INR",
        gross_demo_amount=money(sum((row.eligible_amount for row in rows), Decimal("0"))),
        commission_demo_amount=money(sum((row.commission_amount for row in rows), Decimal("0"))),
        rescuer_demo_share=money(sum((row.rescuer_share for row in rows), Decimal("0"))),
        reversed_demo_amount=money(sum((row.reversed_amount for row in rows), Decimal("0"))),
        withdrawable=False,
        disclaimer="Illustrative demo earnings only. No real payout or withdrawal is available.",
    )


@router.get("/rescuer/transactions", response_model=list[PaymentResponse])
def rescuer_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.RESCUER)),
):
    profile = get_profile_for_user(db, user.id)
    if profile is None:
        raise fail(403, "RESCUER_PROFILE_REQUIRED", "Rescuer profile required")
    rows = db.scalars(
        select(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Booking.rescuer_id == profile.id)
        .order_by(Payment.created_at.desc())
    ).all()
    return [_payment_response(db, row) for row in rows]


@router.get("/admin/payments", response_model=list[PaymentResponse])
def admin_payments(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    rows = db.scalars(select(Payment).order_by(Payment.created_at.desc())).all()
    return [_payment_response(db, row) for row in rows]


@router.get("/admin/ledger")
def admin_ledger(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    rows = db.scalars(
        select(FinancialLedgerEntry).order_by(FinancialLedgerEntry.created_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "transaction_group": row.transaction_group,
            "payment_id": row.payment_id,
            "booking_id": row.booking_id,
            "account_code": row.account_code,
            "direction": row.direction,
            "amount": row.amount,
            "currency": row.currency,
            "description": row.description,
            "is_demo": row.is_demo,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/webhooks/payments/{provider}", status_code=202)
async def payment_webhook(
    provider: str,
    request: Request,
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    x_event_reference: str | None = Header(default=None, alias="X-Event-Reference"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.payment_webhook_secret:
        raise fail(503, "PAYMENT_WEBHOOK_DISABLED", "Payment webhooks are not configured")
    body = await request.body()
    expected = hmac.new(
        settings.payment_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not x_webhook_signature or not hmac.compare_digest(expected, x_webhook_signature.strip()):
        raise fail(401, "INVALID_WEBHOOK_SIGNATURE", "Webhook signature is invalid")
    event_reference = (x_event_reference or "").strip()
    if not event_reference or len(event_reference) > 160:
        raise fail(400, "EVENT_REFERENCE_REQUIRED", "A valid event reference is required")
    existing = db.scalar(
        select(PaymentProviderWebhook).where(
            PaymentProviderWebhook.event_reference == event_reference
        )
    )
    if existing is not None:
        return {"accepted": True, "duplicate": True, "is_demo": True}
    db.add(
        PaymentProviderWebhook(
            provider=provider[:80],
            event_reference=event_reference,
            signature_valid=True,
            sanitized_status="ACCEPTED_DEMO_NO_PROCESSING",
            is_demo=True,
        )
    )
    db.commit()
    return {"accepted": True, "duplicate": False, "is_demo": True}
