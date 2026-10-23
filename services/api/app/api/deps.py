from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token_claims
from app.db.session import get_db
from app.models.entities import Role, User


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    spilton_session: str | None = Cookie(default=None),
) -> User:
    token = spilton_session
    if authorization:
        scheme, separator, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer":
            # A supplied Bearer scheme is authoritative.  Never fall back to a
            # cookie when the header is malformed, because the CSRF middleware
            # intentionally exempts bearer-authenticated clients.
            token = credentials.strip() if separator else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        claims = decode_access_token_claims(token)
        user_id = UUID(claims["sub"])
    except (InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        ) from None
    user = db.get(User, user_id)
    if not user or not user.is_active or claims["ver"] != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        )
    return user


def require_roles(*roles: Role):
    def guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return guard
