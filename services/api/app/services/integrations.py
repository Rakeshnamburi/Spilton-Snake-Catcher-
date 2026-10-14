"""Lazy integration foundations; no external action occurs without configuration."""

import boto3
import redis

from app.core.config import get_settings


class IntegrationNotConfigured(RuntimeError):
    pass


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def s3_client():
    settings = get_settings()
    if not all(
        [settings.s3_endpoint, settings.s3_bucket, settings.s3_access_key, settings.s3_secret_key]
    ):
        raise IntegrationNotConfigured("S3-compatible private media storage is not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def fcm_project_id() -> str:
    project_id = get_settings().fcm_project_id
    if not project_id:
        raise IntegrationNotConfigured("Firebase Cloud Messaging is not configured")
    return project_id
