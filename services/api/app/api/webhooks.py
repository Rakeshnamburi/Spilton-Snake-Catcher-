import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.marketplace_helpers import fail
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import NotificationDeliveryAttempt

router = APIRouter(prefix="/webhooks", tags=["provider webhooks"])


@router.post("/whatsapp")
async def whatsapp_delivery_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
):
    secret = get_settings().whatsapp_webhook_secret
    if not secret:
        raise fail(503, "WEBHOOK_NOT_CONFIGURED", "WhatsApp webhook verification is not configured")
    body = await request.body()
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not x_hub_signature_256 or not hmac.compare_digest(expected, x_hub_signature_256):
        raise fail(401, "INVALID_WEBHOOK_SIGNATURE", "Webhook signature validation failed")
    payload = await request.json()
    message_id = str(payload.get("message_id", ""))[:255]
    status = str(payload.get("status", ""))[:30].upper()
    if not message_id or status not in {"DELIVERED", "FAILED", "READ"}:
        raise fail(422, "INVALID_WEBHOOK_PAYLOAD", "Unsupported delivery update")
    attempt = db.scalar(
        select(NotificationDeliveryAttempt).where(
            NotificationDeliveryAttempt.provider_message_id == message_id,
            NotificationDeliveryAttempt.channel == "WHATSAPP",
        )
    )
    if attempt is None:
        return {"accepted": True, "matched": False}
    attempt.status = status
    attempt.sanitized_result = "Verified provider status update received."
    db.commit()
    return {"accepted": True, "matched": True}
