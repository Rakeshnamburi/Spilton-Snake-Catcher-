"""Private incident-media validation and storage.

Objects are never placed in an application public directory.  Both adapters expose
only opaque keys; authorization remains the responsibility of the API route.
"""

from __future__ import annotations

import io
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import UUID

from botocore.exceptions import ClientError
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.services.integrations import IntegrationNotConfigured, s3_client

MAX_MEDIA_BYTES = 5 * 1024 * 1024
MAX_MEDIA_PER_INCIDENT = 3
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

CONTENT_TYPES = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


class MediaValidationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredObject:
    body: bytes
    content_type: str


class PrivateMediaStorage(Protocol):
    def put(self, key: str, body: bytes, content_type: str) -> None: ...

    def get(self, key: str, content_type: str) -> StoredObject: ...

    def delete(self, key: str) -> None: ...


def _safe_storage_key(key: str) -> PurePosixPath:
    parsed = PurePosixPath(key)
    if parsed.is_absolute() or ".." in parsed.parts or not parsed.parts:
        raise StorageError("Invalid private storage key")
    if any(not re.fullmatch(r"[A-Za-z0-9._-]+", part) for part in parsed.parts):
        raise StorageError("Invalid private storage key")
    return parsed


class LocalPrivateMediaStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        parsed = _safe_storage_key(key)
        path = self.root.joinpath(*parsed.parts).resolve()
        if self.root != path and self.root not in path.parents:
            raise StorageError("Invalid private storage key")
        return path

    def put(self, key: str, body: bytes, content_type: str) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(body)
        except FileExistsError as error:
            raise StorageError("Private storage key already exists") from error
        except OSError as error:
            path.unlink(missing_ok=True)
            raise StorageError("Could not write private media object") from error

    def get(self, key: str, content_type: str) -> StoredObject:
        try:
            body = self._path(key).read_bytes()
        except FileNotFoundError as error:
            raise StorageError("Private media object is missing") from error
        return StoredObject(body=body, content_type=content_type)

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as error:
            raise StorageError("Could not remove private media object") from error


class S3PrivateMediaStorage:
    def __init__(self):
        settings = get_settings()
        if not settings.s3_bucket:
            raise IntegrationNotConfigured("S3-compatible private media storage is not configured")
        self.bucket = settings.s3_bucket
        self.client = s3_client()

    def put(self, key: str, body: bytes, content_type: str) -> None:
        _safe_storage_key(key)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def get(self, key: str, content_type: str) -> StoredObject:
        _safe_storage_key(key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise StorageError("Private media object is missing") from error
            raise
        return StoredObject(body=response["Body"].read(), content_type=content_type)

    def delete(self, key: str) -> None:
        _safe_storage_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)


def get_media_storage() -> PrivateMediaStorage:
    settings = get_settings()
    if settings.media_storage_backend == "s3":
        return S3PrivateMediaStorage()
    return LocalPrivateMediaStorage(settings.private_media_dir)


def make_storage_key(incident_id: UUID, extension: str) -> str:
    return f"incidents/{incident_id}/{secrets.token_hex(24)}{extension}"


def _signature_format(body: bytes) -> str | None:
    if body.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "WEBP"
    return None


def validate_and_sanitize_image(
    body: bytes, declared_content_type: str | None
) -> tuple[bytes, str, str]:
    """Verify signature and pixels, then re-encode without EXIF or ancillary metadata."""

    if not body:
        raise MediaValidationError("EMPTY_FILE", "The uploaded image is empty")
    if len(body) > MAX_MEDIA_BYTES:
        raise MediaValidationError("FILE_TOO_LARGE", "Images must be 5 MB or smaller")

    image_format = _signature_format(body)
    if image_format is None:
        raise MediaValidationError(
            "UNSUPPORTED_IMAGE", "Only valid JPEG, PNG, and WebP images are accepted"
        )
    canonical_type, extension = CONTENT_TYPES[image_format]
    normalized_declared_type = (declared_content_type or "").split(";", 1)[0].lower().strip()
    if normalized_declared_type and normalized_declared_type != canonical_type:
        raise MediaValidationError(
            "CONTENT_TYPE_MISMATCH", "The declared image type does not match its file signature"
        )

    try:
        with Image.open(io.BytesIO(body)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(body)) as source:
            if source.format != image_format:
                raise MediaValidationError(
                    "CONTENT_TYPE_MISMATCH", "The image format does not match its file signature"
                )
            if getattr(source, "n_frames", 1) != 1:
                raise MediaValidationError("ANIMATED_IMAGE", "Animated images are not accepted")
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise MediaValidationError("IMAGE_TOO_LARGE", "Image dimensions are too large")
            clean = ImageOps.exif_transpose(source)
            clean.load()
            output = io.BytesIO()
            if image_format == "JPEG":
                if clean.mode not in {"RGB", "L"}:
                    clean = clean.convert("RGB")
                clean.save(output, format="JPEG", quality=90, optimize=True)
            elif image_format == "PNG":
                clean.save(output, format="PNG", optimize=True)
            else:
                clean.save(output, format="WEBP", quality=90, method=4)
    except MediaValidationError:
        raise
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as error:
        raise MediaValidationError(
            "INVALID_IMAGE", "The uploaded file is not a valid image"
        ) from error

    sanitized = output.getvalue()
    if not sanitized or len(sanitized) > MAX_MEDIA_BYTES:
        raise MediaValidationError(
            "SANITIZED_FILE_TOO_LARGE", "The safely processed image exceeds the 5 MB limit"
        )
    return sanitized, canonical_type, extension


def safe_original_filename(filename: str | None, extension: str) -> str:
    candidate = Path((filename or "image").replace("\x00", "")).name.strip()
    stem = Path(candidate).stem[:180] or "image"
    stem = re.sub(r"[^A-Za-z0-9 _.-]", "_", stem).strip(" .") or "image"
    return f"{stem}{extension}"
