from typing import Any

from fastapi import HTTPException


class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        detail: dict[str, Any] = {"code": code, "message": message}
        if details is not None:
            detail["details"] = details
        super().__init__(status_code=status_code, detail=detail, headers=headers)
