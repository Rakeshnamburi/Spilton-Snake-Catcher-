import hmac
import json
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth_social import router as auth_social_router
from app.api.messages import router as messages_router
from app.api.routes import router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.request_limits import (
    MediaRequestSizeLimitMiddleware,
    RequestBodyTooLarge,
    media_request_too_large_response,
)

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description=(
        "Shared DEMO-mode API for SPILTON web and mobile clients. "
        "No endpoint performs live rescue dispatch."
    ),
)

CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/otp/request",
    "/api/v1/auth/otp/verify",
    "/api/v1/auth/oauth/exchange",
}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a safe correlation id, minimal security headers, and PII-free access logs."""

    supplied_id = request.headers.get("x-request-id", "")
    request_id = supplied_id if REQUEST_ID_PATTERN.fullmatch(supplied_id) else uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    logger.info(
        json.dumps(
            {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
            separators=(",", ":"),
        )
    )
    return response


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    """Double-submit protection for cookie sessions; bearer clients are unaffected."""

    authorization = request.headers.get("authorization", "")
    uses_bearer = authorization.lower().startswith("bearer ")
    session_cookie = request.cookies.get("spilton_session")
    if (
        request.method in UNSAFE_METHODS
        and request.url.path not in CSRF_EXEMPT_PATHS
        and session_cookie
        and not uses_bearer
    ):
        cookie_token = request.cookies.get("spilton_csrf", "")
        header_token = request.headers.get("x-csrf-token", "")
        if (
            not cookie_token
            or not header_token
            or not hmac.compare_digest(cookie_token, header_token)
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "A valid CSRF token is required for this request",
                    }
                },
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MediaRequestSizeLimitMiddleware)
app.include_router(router)
app.include_router(auth_social_router)
app.include_router(messages_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    """Readiness verifies the source-of-truth database without leaking configuration."""

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness database check failed")
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready", "database": "ok", "mode": "DEMO"}


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and {"code", "message"} <= exc.detail.keys():
        error = exc.detail
    else:
        error = {"code": "HTTP_ERROR", "message": str(exc.detail)}
    error["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=exc.status_code, content={"error": error}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"] if part != "body"),
            "message": item["msg"],
            "type": item["type"],
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request contains invalid data",
                "details": details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RequestBodyTooLarge)
async def request_body_too_large(request: Request, _: RequestBodyTooLarge):
    del request
    return media_request_too_large_response()


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled API error request_id=%s", request_id, exc_info=error)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
    )
