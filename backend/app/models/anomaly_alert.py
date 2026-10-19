"""
app/models/anomaly_alert.py
────────────────────────────
Created when the anomaly engine flags a trade as statistically unusual.
HIGH-risk alerts also trigger an SNS notification.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.investigation import Investigation
    from app.models.trade import Trade


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    trade_id: Mapped[int] = mapped_column(Integer, ForeignKey("trades.id"), unique=True, nullable=False, index=True)
    trade: Mapped[Trade] = relationship("Trade", back_populates="alert")

    # Scores (all project-defined, not regulatory standards)
    notional_zscore: Mapped[float] = mapped_column(Float, nullable=True)
    quantity_zscore: Mapped[float] = mapped_column(Float, nullable=True)
    statistical_score: Mapped[float] = mapped_column(Float, nullable=True)   # 0–1, stat composite
    ml_score: Mapped[float] = mapped_column(Float, nullable=True)             # 0–1, isolation forest
    context_score: Mapped[float] = mapped_column(Float, nullable=True)        # 0–1, contextual
    combined_score: Mapped[float] = mapped_column(Float, nullable=True)       # weighted composite

    # Risk classification (project-defined thresholds, not regulatory standards)
    risk_level: Mapped[str] = mapped_column(
        Enum("LOW", "MEDIUM", "HIGH", name="risk_level_enum"),
        nullable=False,
        index=True,
    )

    # Human-readable explanation for the dashboard
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Workflow status
    status: Mapped[str] = mapped_column(
        Enum("OPEN", "UNDER_REVIEW", "CLOSED", name="alert_status_enum"),
        default="OPEN",
        nullable=False,
        index=True,
    )

    # SNS notification tracking
    sns_notified: Mapped[bool] = mapped_column(Integer, default=False, nullable=False)

    # Relationship to investigation
    investigation_id: Mapped[int] = mapped_column(Integer, ForeignKey("investigations.id"), nullable=True)
    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<AnomalyAlert trade_id={self.trade_id} risk={self.risk_level} score={self.combined_score:.3f}>"
