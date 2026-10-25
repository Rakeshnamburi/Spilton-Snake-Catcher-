from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
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
    demo_mode: Literal[True] = True
    media_storage_backend: str = "local"
    private_media_dir: str = "./.private_media"
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    fcm_project_id: str | None = None
    fcm_service_account_json: str | None = None
    authorized_operation_enabled: Literal[False] = False
    pricing_authorized: Literal[False] = False
    payments_enabled: Literal[False] = False
    default_commission_percent: str = "10.00"
    booking_response_minutes: int = 15
    rescuer_stale_minutes: int = 30
    email_provider_api_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    demo_email_recipient: str | None = None
    sms_provider_api_key: str | None = None
    sms_provider_url: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_provider_url: str | None = None
    whatsapp_webhook_secret: str | None = None
    whatsapp_template_booking: str | None = None
    notification_max_attempts: int = 3
    public_web_url: str = "http://localhost:3000"
    tracking_session_minutes: int = 180
    tracking_min_update_seconds: int = 5
    tracking_retention_hours: int = 24
    routing_provider_url: str | None = None
    routing_api_key: str | None = None
    routing_cache_seconds: int = 60
    evidence_retention_days: int = 30
    payment_webhook_secret: str | None = None
    error_monitoring_dsn: str | None = None

    # --- Email OTP sign-in -------------------------------------------------
    otp_length: int = 6
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 30

    # --- Social / OAuth sign-in --------------------------------------------
    # api_public_url is the browser-reachable base URL of THIS API. OAuth
    # providers redirect back to "{api_public_url}/api/v1/auth/oauth/{p}/callback".
    api_public_url: str = "http://localhost:8000"
    web_app_url: str = "http://localhost:3000"
    mobile_app_scheme: str = "spilton"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    microsoft_tenant: str = "common"
    oauth_state_ttl_minutes: int = 15

    @field_validator(
        "demo_mode",
        "authorized_operation_enabled",
        "pricing_authorized",
        "payments_enabled",
        mode="before",
    )
    @classmethod
    def coerce_literal_bool(cls, value: object) -> object:
        """Accept the string values pydantic-settings reads from a .env file.

        pydantic does not coerce "true"/"false" strings into a Literal[True] /
        Literal[False] field, so copying `.env.example` verbatim (which sets
        DEMO_MODE=true, AUTHORIZED_OPERATION_ENABLED=false, ...) previously made
        the whole API fail to boot. Coercing here keeps the safety constraints
        intact while allowing the documented env file to load.
        """
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @property
    def social_login_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def microsoft_login_enabled(self) -> bool:
        return bool(self.microsoft_client_id and self.microsoft_client_secret)

    @property
    def email_otp_enabled(self) -> bool:
        return True

    @property
    def smtp_configured(self) -> bool:
        return all(
            [
                self.smtp_host,
                self.smtp_username,
                self.smtp_password,
                self.smtp_from_address,
            ]
        )

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

    @model_validator(mode="after")
    def production_security_guard(self):
        if self.environment.lower() not in {"production", "staging"}:
            return self
        if self.jwt_secret == "development-only-secret-change-me-32-chars":
            raise ValueError("JWT_SECRET must be replaced outside development")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true outside development")
        if not self.origins or any(
            origin == "*" or not origin.startswith("https://") for origin in self.origins
        ):
            raise ValueError("WEB_ORIGINS must contain explicit HTTPS origins outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
