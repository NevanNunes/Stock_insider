"""
app/db/base.py
──────────────
SQLAlchemy declarative base — imported by all models.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
