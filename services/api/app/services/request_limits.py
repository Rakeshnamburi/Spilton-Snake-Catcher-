"""ASGI request limits applied before multipart parsing can spool a large upload."""

from typing import Any

from fastapi.responses import JSONResponse

from app.services.media_storage import MAX_MEDIA_BYTES

MAX_MEDIA_REQUEST_BYTES = MAX_MEDIA_BYTES + 1024 * 1024
MAX_RESCUER_DOCUMENT_REQUEST_BYTES = 11 * 1024 * 1024


class RequestBodyTooLarge(Exception):
    pass


def _request_limit(scope: dict[str, Any]) -> int | None:
    if scope.get("type") != "http" or scope.get("method") != "POST":
        return None
    parts = str(scope.get("path", "")).rstrip("/").split("/")
    if len(parts) == 6 and parts[1:4] == ["api", "v1", "incidents"] and parts[5] == "media":
        return MAX_MEDIA_REQUEST_BYTES
    if parts == ["", "api", "v1", "rescuers", "onboarding", "documents"]:
        return MAX_RESCUER_DOCUMENT_REQUEST_BYTES
    return None


def media_request_too_large_response() -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={
            "error": {
                "code": "REQUEST_TOO_LARGE",
                "message": "The media upload request is too large",
            }
        },
    )


class MediaRequestSizeLimitMiddleware:
    """Cap the whole multipart request before FastAPI parses and spools it."""

    def __init__(self, app, max_bytes: int = MAX_MEDIA_REQUEST_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        request_limit = _request_limit(scope)
        if request_limit is None:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                declared_length = int(content_length)
            except ValueError:
                declared_length = 0
            if declared_length > request_limit:
                response = media_request_too_large_response()
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> dict[str, Any]:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > request_limit:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = media_request_too_large_response()
            await response(scope, receive, send)
