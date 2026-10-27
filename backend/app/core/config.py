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

    # RDS PostgreSQL credentials loaded from Parameter Store
    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""

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
    SSM_PARAM_PREFIX: str = "/market-surveillance/prod/"

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
    """Load production configuration from AWS Systems Manager Parameter Store."""
    if not s.USE_PARAMETER_STORE:
        return

    import logging
    import boto3
    from urllib.parse import quote_plus

    logger = logging.getLogger(__name__)

    try:
        ssm = boto3.client("ssm", region_name=s.AWS_REGION)

        paginator = ssm.get_paginator("get_parameters_by_path")

        parameters = {}

        for page in paginator.paginate(
            Path=s.SSM_PARAM_PREFIX,
            WithDecryption=True,
            Recursive=True,
        ):
            for parameter in page.get("Parameters", []):
                name = parameter["Name"].removeprefix(
                    s.SSM_PARAM_PREFIX
                ).strip("/").upper()

                parameters[name] = parameter["Value"]

        # Load ordinary application settings explicitly.
        if "AWS_REGION" in parameters:
            s.AWS_REGION = parameters["AWS_REGION"]

        if "SECRET_KEY" in parameters:
            s.SECRET_KEY = parameters["SECRET_KEY"]

        if "SQS_QUEUE_URL" in parameters:
            s.SQS_QUEUE_URL = parameters["SQS_QUEUE_URL"]

        if "SNS_TOPIC_ARN" in parameters:
            s.SNS_TOPIC_ARN = parameters["SNS_TOPIC_ARN"]

        if "S3_BUCKET" in parameters:
            s.S3_BUCKET_NAME = parameters["S3_BUCKET"]

        # Load RDS connection settings.
        s.DB_HOST = parameters.get("DB_HOST", s.DB_HOST)
        s.DB_PORT = int(parameters.get("DB_PORT", s.DB_PORT))
        s.DB_NAME = parameters.get("DB_NAME", s.DB_NAME)
        s.DB_USER = parameters.get("DB_USER", s.DB_USER)
        s.DB_PASSWORD = parameters.get("DB_PASSWORD", s.DB_PASSWORD)

        # Refuse to continue with an incomplete production database config.
        required = {
            "DB_HOST": s.DB_HOST,
            "DB_NAME": s.DB_NAME,
            "DB_USER": s.DB_USER,
            "DB_PASSWORD": s.DB_PASSWORD,
        }

        missing = [
            name for name, value in required.items()
            if not value
        ]

        if missing:
            raise RuntimeError(
                "Missing required database parameters: "
                + ", ".join(missing)
            )

        # IMPORTANT:
        # Use the PostgreSQL SQLAlchemy driver installed by your
        # backend requirements. This example assumes psycopg2-binary.
        database_url = (
            f"postgresql+psycopg2://"
            f"{quote_plus(s.DB_USER)}:"
            f"{quote_plus(s.DB_PASSWORD)}@"
            f"{s.DB_HOST}:{s.DB_PORT}/"
            f"{quote_plus(s.DB_NAME)}"
        )

        s.DATABASE_URL = database_url

        logger.info(
            "Production configuration loaded from Parameter Store."
        )
        logger.info("Database configuration loaded for RDS.")

    except Exception:
        logger.exception(
            "Failed to load production configuration from Parameter Store."
        )
        raise

settings = Settings()
load_from_ssm(settings)
