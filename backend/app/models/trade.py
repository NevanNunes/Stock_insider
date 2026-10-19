"""
app/models/trade.py
────────────────────
A single synthetic trade event submitted via the Trader Terminal or generator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.anomaly_alert import AnomalyAlert
    from app.models.trader_account import TraderAccount


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trade_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Foreign key to simulated market participant
    trader_id: Mapped[str] = mapped_column(String(16), ForeignKey("trader_accounts.trader_id"), nullable=False, index=True)
    trader: Mapped[TraderAccount] = relationship("TraderAccount", back_populates="trades")

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(Enum("BUY", "SELL", name="trade_side"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    notional_value: Mapped[float] = mapped_column(Float, nullable=False)  # quantity × price
    sector: Mapped[str] = mapped_column(String(64), nullable=True)
    market_session: Mapped[str] = mapped_column(String(16), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc)
    )

    # Source tracking
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(
        Enum("MANUAL", "RANDOM_SUSPICIOUS", "RANDOM_NORMAL", "BULK_GENERATED", name="trade_source"),
        default="MANUAL",
        nullable=False,
    )

    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    alert: Mapped["AnomalyAlert"] = relationship("AnomalyAlert", back_populates="trade", uselist=False)  # noqa: F821

    def __repr__(self) -> str:
        return f"<Trade {self.trade_code} {self.side} {self.quantity}x{self.symbol} @ ₹{self.price:.2f}>"
