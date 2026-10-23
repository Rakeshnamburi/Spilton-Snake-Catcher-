from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.marketplace_helpers import fail
from app.core.security import keyed_digest
from app.db.session import get_db
from app.models.entities import DeviceRegistration, User
from app.schemas.day4 import DeviceRegister, DeviceResponse
from app.services.rate_limit import rate_limiter

router = APIRouter(prefix="/devices", tags=["devices"])


def _response(device: DeviceRegistration) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        platform=device.platform,
        device_label=device.device_label,
        token_hint=f"…{device.token_value[-4:]}",
        is_active=device.is_active,
        last_seen_at=device.last_seen_at,
    )


@router.post("/register", response_model=DeviceResponse)
def register_device(
    payload: DeviceRegister,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    retry = rate_limiter.check(
        f"device-register:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=20,
        window_seconds=3600,
    )
    if retry is not None:
        raise fail(429, "RATE_LIMITED", "Too many device registration attempts")
    token_hash = keyed_digest(f"device:{payload.token}")
    device = db.scalar(
        select(DeviceRegistration).where(
            DeviceRegistration.user_id == user.id,
            DeviceRegistration.token_hash == token_hash,
        )
    )
    now = datetime.now(timezone.utc)
    if device is None:
        device = DeviceRegistration(
            user_id=user.id,
            platform=payload.platform,
            token_hash=token_hash,
            token_value=payload.token,
            device_label=payload.device_label,
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.platform = payload.platform
        device.device_label = payload.device_label
        device.is_active = True
        device.invalidated_at = None
        device.last_seen_at = now
    db.commit()
    db.refresh(device)
    return _response(device)


@router.delete("/{device_id}", status_code=204)
def delete_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = db.get(DeviceRegistration, device_id)
    if device is None or device.user_id != user.id:
        raise fail(404, "DEVICE_NOT_FOUND", "Device registration not found")
    device.is_active = False
    device.invalidated_at = datetime.now(timezone.utc)
    db.commit()
