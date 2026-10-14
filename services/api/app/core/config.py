from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "SPILTON Snake Rescue API"
    environment: str = "development"
    database_url: str = "sqlite:///./spilton.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-secret-change-me-32-chars"
    access_token_minutes: int = 30
    web_origins: str = "http://localhost:3000,http://localhost:8081"
    cookie_secure: bool = False
    demo_mode: bool = True
    media_storage_backend: str = "local"
    private_media_dir: str = "./.private_media"
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    fcm_project_id: str | None = None
    authorized_operation_enabled: Literal[False] = False
    pricing_authorized: Literal[False] = False
    payments_enabled: Literal[False] = False
    default_commission_percent: str = "10.00"
    booking_response_minutes: int = 15
    rescuer_stale_minutes: int = 30
    email_provider_api_key: str | None = None
    sms_provider_api_key: str | None = None
    whatsapp_access_token: str | None = None

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.web_origins.split(",") if item.strip()]

    @field_validator("media_storage_backend")
    @classmethod
    def validate_media_backend(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"local", "s3"}:
            raise ValueError("MEDIA_STORAGE_BACKEND must be 'local' or 's3'")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
