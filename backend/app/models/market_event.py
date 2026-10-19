"""
app/models/market_event.py
───────────────────────────
Synthetic market events (Earnings, Mergers, etc.) seeded from data/market_events.csv.
Used by the contextual anomaly detector to flag pre-event trading.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketEvent(Base):
    __tablename__ = "market_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(
        Enum(
            "EARNINGS", "MERGER", "ACQUISITION", "MANAGEMENT_ANNOUNCEMENT",
            "MAJOR_CONTRACT", "REGULATORY_ANNOUNCEMENT", "PRODUCT_LAUNCH",
            "DIVIDEND_ANNOUNCEMENT", "COMPANY_NEWS",
            name="event_type_enum",
        ),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum("LOW", "MEDIUM", "HIGH", name="event_severity_enum"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<MarketEvent {self.symbol} {self.event_type} @ {self.event_time}>"
