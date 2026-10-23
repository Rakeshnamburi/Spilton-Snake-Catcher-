from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class GatewayResult:
    status: str
    provider_reference: str | None
    sanitized_message: str


class PaymentGateway(Protocol):
    def authorize(
        self,
        *,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> GatewayResult: ...


class DemoPaymentGateway:
    """Local-only adapter that never accepts credentials or moves money."""

    def authorize(
        self,
        *,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> GatewayResult:
        del amount, currency, idempotency_key
        return GatewayResult(
            status="DEMO_SUCCEEDED",
            provider_reference=None,
            sanitized_message="Local demo success; no payment provider was contacted.",
        )


def get_payment_gateway() -> PaymentGateway:
    settings = get_settings()
    if settings.payments_enabled:
        raise RuntimeError(
            "Real payment gateway activation is intentionally unavailable in this sprint"
        )
    return DemoPaymentGateway()
