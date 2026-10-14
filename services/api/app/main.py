import hmac
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import get_settings
from app.services.request_limits import (
    MediaRequestSizeLimitMiddleware,
    RequestBodyTooLarge,
    media_request_too_large_response,
)

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Shared DEMO-mode API for SPILTON web and mobile clients. "
        "No endpoint performs live rescue dispatch."
    ),
)

CSRF_EXEMPT_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and {"code", "message"} <= exc.detail.keys():
        error = exc.detail
    else:
        error = {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
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
            }
        },
    )


@app.exception_handler(RequestBodyTooLarge)
async def request_body_too_large(request: Request, _: RequestBodyTooLarge):
    del request
    return media_request_too_large_response()


@app.exception_handler(Exception)
async def unexpected_error(_: Request, error: Exception):
    logger.exception("Unhandled API error", exc_info=error)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )
