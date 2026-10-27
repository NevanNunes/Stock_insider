"""
app/core/config.py
──────────────────
Centralised settings loaded from .env (local) or AWS Parameter Store (cloud).
All AWS service toggles are driven by whether the relevant env var is set.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "MarketSurveillanceAPI"
    APP_ENV: str = "local"          # "local" | "production"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./market_surveillance.db"

    # ── AWS (all optional — blank → local stubs) ──────────────────────────────
    AWS_REGION: str = "ap-south-1"
    SQS_QUEUE_URL: str = ""
    SNS_TOPIC_ARN: str = ""
    S3_BUCKET_NAME: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # ── Data paths ────────────────────────────────────────────────────────────
    DATA_DIR: str = "../data"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Anomaly Detection thresholds (project-defined, not regulatory) ────────
    Z_LOW_THRESHOLD: float = 2.0
    Z_HIGH_THRESHOLD: float = 3.0
    IF_CONTAMINATION: float = 0.05
    IF_RANDOM_STATE: int = 42
    W_STAT: float = 0.40   # weight: statistical score
    W_ML: float = 0.40     # weight: isolation forest score
    W_CTX: float = 0.20    # weight: contextual score

    # ── Local storage fallback ────────────────────────────────────────────────
    LOCAL_STORAGE_DIR: str = "./storage/reports"

    # ── AWS Systems Manager Parameter Store ───────────────────────────────────
    USE_PARAMETER_STORE: bool = False
    SSM_PARAM_PREFIX: str = "/market_surveillance/"

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def is_local(self) -> bool:
        return self.APP_ENV == "local"

    @property
    def use_sqs(self) -> bool:
        return bool(self.SQS_QUEUE_URL)

    @property
    def use_sns(self) -> bool:
        return bool(self.SNS_TOPIC_ARN)

    @property
    def use_s3(self) -> bool:
        return bool(self.S3_BUCKET_NAME)

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def data_path(self) -> Path:
        return Path(self.DATA_DIR).resolve()


def load_from_ssm(s: Settings) -> None:
    """Fetch configuration directly from AWS Systems Manager Parameter Store if enabled."""
    if not s.USE_PARAMETER_STORE:
        return
    try:
        import boto3
        import logging
        logger = logging.getLogger(__name__)
        kwargs = {"region_name": s.AWS_REGION}
        if s.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = s.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = s.AWS_SECRET_ACCESS_KEY
        ssm = boto3.client("ssm", **kwargs)
        paginator = ssm.get_paginator("get_parameters_by_path")
        for page in paginator.paginate(Path=s.SSM_PARAM_PREFIX, WithDecryption=True, Recursive=True):
            for p in page.get("Parameters", []):
                key = p["Name"].removeprefix(s.SSM_PARAM_PREFIX).strip("/").upper()
                if hasattr(s, key):
                    setattr(s, key, p["Value"])
                    logger.info("Loaded SSM parameter: %s", key)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Could not load from SSM Parameter Store: %s", exc)


settings = Settings()
load_from_ssm(settings)
