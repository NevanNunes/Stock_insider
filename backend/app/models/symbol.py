"""
app/models/symbol.py
─────────────────────
Fictional stock symbol seeded from data/symbols.csv.
Used for the Trader Terminal dropdown and price lookups.
"""
from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sector: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_price: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    average_daily_volume: Mapped[float] = mapped_column(Float, nullable=False)
    typical_spread: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<Symbol {self.symbol} @ ₹{self.baseline_price:.2f}>"
