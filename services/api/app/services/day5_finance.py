from __future__ import annotations

import secrets
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Booking,
    CommissionEntry,
    FinancialLedgerEntry,
    Payment,
    RescuerProfile,
    SettlementAccount,
    SettlementEntry,
)

CENT = Decimal("0.01")


def money(value: Decimal | str | int) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def commission_amount(amount: Decimal, rate_percent: Decimal) -> Decimal:
    return money(money(amount) * Decimal(rate_percent) / Decimal("100"))


def _ledger(
    db: Session,
    *,
    group: str,
    payment: Payment,
    account_code: str,
    direction: str,
    amount: Decimal,
    description: str,
) -> None:
    db.add(
        FinancialLedgerEntry(
            transaction_group=group,
            payment_id=payment.id,
            booking_id=payment.booking_id,
            account_code=account_code,
            direction=direction,
            amount=money(amount),
            currency=payment.currency,
            description=description,
            is_demo=True,
        )
    )


def record_demo_payment_accounting(
    db: Session,
    *,
    payment: Payment,
    booking: Booking,
    profile: RescuerProfile,
) -> CommissionEntry:
    existing = db.scalar(select(CommissionEntry).where(CommissionEntry.payment_id == payment.id))
    if existing is not None:
        return existing

    gross = money(payment.amount)
    rate = Decimal(booking.commission_rate_snapshot)
    commission = commission_amount(gross, rate)
    rescuer_share = money(gross - commission)
    entry = CommissionEntry(
        payment_id=payment.id,
        booking_id=booking.id,
        rate_snapshot=rate,
        eligible_amount=gross,
        commission_amount=commission,
        rescuer_share=rescuer_share,
        reversed_amount=Decimal("0.00"),
        status="DEMO_RECORDED",
        settlement_status="NOT_SETTLED",
        currency=payment.currency,
        is_demo=True,
    )
    db.add(entry)
    db.flush()

    account = db.scalar(
        select(SettlementAccount).where(
            SettlementAccount.rescuer_id == profile.id,
            SettlementAccount.currency == payment.currency,
        )
    )
    if account is None:
        account = SettlementAccount(
            rescuer_id=profile.id,
            currency=payment.currency,
            status="DEMO_ONLY",
            withdrawable=False,
        )
        db.add(account)
        db.flush()
    db.add(
        SettlementEntry(
            settlement_account_id=account.id,
            commission_entry_id=entry.id,
            amount=rescuer_share,
            status="PENDING_DEMO",
            is_demo=True,
        )
    )

    group = f"PAY-{secrets.token_hex(12)}"
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="DEMO_CLEARING",
        direction="DEBIT",
        amount=gross,
        description="Demo payment clearing entry; no money moved.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="CUSTOMER_DEMO_PAYMENT",
        direction="CREDIT",
        amount=gross,
        description="Demo customer payment entry.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="BOOKING_SERVICE",
        direction="DEBIT",
        amount=gross,
        description="Illustrative demo service allocation.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="PLATFORM_COMMISSION",
        direction="CREDIT",
        amount=commission,
        description="Illustrative platform commission; not withdrawable.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="RESCUER_SHARE",
        direction="CREDIT",
        amount=rescuer_share,
        description="Illustrative rescuer share; not withdrawable.",
    )
    return entry


def record_demo_refund_accounting(
    db: Session,
    *,
    payment: Payment,
    commission: CommissionEntry,
    refund_amount: Decimal,
) -> None:
    refund = money(refund_amount)
    reversed_commission = commission_amount(refund, Decimal(commission.rate_snapshot))
    reversed_share = money(refund - reversed_commission)
    group = f"REF-{secrets.token_hex(12)}"
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="CUSTOMER_REFUND",
        direction="DEBIT",
        amount=refund,
        description="Demo refund record; no money moved.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="DEMO_CLEARING",
        direction="CREDIT",
        amount=refund,
        description="Demo clearing reversal.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="PLATFORM_COMMISSION_REVERSAL",
        direction="DEBIT",
        amount=reversed_commission,
        description="Illustrative commission reversal.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="RESCUER_SHARE_REVERSAL",
        direction="DEBIT",
        amount=reversed_share,
        description="Illustrative rescuer-share reversal.",
    )
    _ledger(
        db,
        group=group,
        payment=payment,
        account_code="BOOKING_SERVICE_REVERSAL",
        direction="CREDIT",
        amount=refund,
        description="Illustrative service allocation reversal.",
    )
    commission.reversed_amount = money(
        Decimal(commission.reversed_amount or 0) + reversed_commission
    )
    if money(payment.refunded_amount + refund) >= money(payment.amount):
        commission.status = "DEMO_REVERSED"
        commission.settlement_status = "REVERSED_DEMO"


def ledger_group_is_balanced(db: Session, transaction_group: str) -> bool:
    debit = db.scalar(
        select(func.coalesce(func.sum(FinancialLedgerEntry.amount), 0)).where(
            FinancialLedgerEntry.transaction_group == transaction_group,
            FinancialLedgerEntry.direction == "DEBIT",
        )
    )
    credit = db.scalar(
        select(func.coalesce(func.sum(FinancialLedgerEntry.amount), 0)).where(
            FinancialLedgerEntry.transaction_group == transaction_group,
            FinancialLedgerEntry.direction == "CREDIT",
        )
    )
    return money(Decimal(debit)) == money(Decimal(credit))
