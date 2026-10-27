"""
app/db/session.py
──────────────────
SQLAlchemy engine + session factory.
Works with SQLite locally and PostgreSQL (RDS) in production — 
only the DATABASE_URL env var changes between environments.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# SQLite needs check_same_thread=False; PostgreSQL ignores this kwarg
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,    # Tests connection liveness to handle RDS idle timeouts gracefully
    echo=settings.DEBUG,   # prints SQL queries in debug mode — disable in prod
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
