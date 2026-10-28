"""
app/models/trader_account.py
──────────────────────────────
Simulated market participant whose trades are being watched.
Seeded from data/traders.csv at startup.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trade import Trade


class TraderAccount(Base):
    __tablename__ = "trader_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trader_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)  # e.g. TRD001
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # set when created via registration
    trader_type: Mapped[str] = mapped_column(String(64), nullable=False)   # archetype
    preferred_symbols: Mapped[str] = mapped_column(Text, nullable=True)    # semicolon-separated
    preferred_sectors: Mapped[str] = mapped_column(Text, nullable=True)
    preferred_start_time: Mapped[str] = mapped_column(String(8), nullable=True)
    preferred_end_time: Mapped[str] = mapped_column(String(8), nullable=True)
    buy_probability: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Historical baseline stats (from data/traders.csv — frozen from the 90-day history)
    hist_mean_quantity: Mapped[float] = mapped_column(Float, nullable=True)
    hist_std_quantity: Mapped[float] = mapped_column(Float, nullable=True)
    hist_mean_notional: Mapped[float] = mapped_column(Float, nullable=True)
    hist_std_notional: Mapped[float] = mapped_column(Float, nullable=True)
    hist_trade_count: Mapped[int] = mapped_column(Integer, default=0)

    # Profile defaults (used by the random trade generator)
    average_trade_quantity: Mapped[float] = mapped_column(Float, nullable=True)
    quantity_std: Mapped[float] = mapped_column(Float, nullable=True)
    average_notional: Mapped[float] = mapped_column(Float, nullable=True)
    notional_std: Mapped[float] = mapped_column(Float, nullable=True)
    normal_trades_per_day: Mapped[float] = mapped_column(Float, nullable=True)

    # relationships
    trades: Mapped[list[Trade]] = relationship("Trade", back_populates="trader")

    def __repr__(self) -> str:
        return f"<TraderAccount {self.trader_id} ({self.trader_type})>"
