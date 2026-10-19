"""
app/models/investigation.py
────────────────────────────
Tracks human analyst follow-up on one or more anomaly alerts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.anomaly_alert import AnomalyAlert
    from app.models.user import User


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    opened_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    opened_by_user: Mapped[User] = relationship("User", back_populates="investigations")

    status: Mapped[str] = mapped_column(
        Enum("OPEN", "UNDER_REVIEW", "CLOSED", name="investigation_status_enum"),
        default="OPEN",
        nullable=False,
        index=True,
    )

    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # S3 report reference (populated after Export Compliance Report is triggered)
    report_s3_key: Mapped[str] = mapped_column(Text, nullable=True)
    report_url: Mapped[str] = mapped_column(Text, nullable=True)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    alerts: Mapped[list[AnomalyAlert]] = relationship(
        "AnomalyAlert", back_populates="investigation"
    )

    def __repr__(self) -> str:
        return f"<Investigation id={self.id} status={self.status}>"
