"""
app/schemas/trade.py — Request/response schemas for trades
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ── Requests ──────────────────────────────────────────────────────────────────

class ManualTradeRequest(BaseModel):
    """Submitted from the Trader Terminal manual entry form."""
    trader_id: str          # e.g. "TRD001"
    symbol: str             # e.g. "ALPHATECH"
    side: str               # "BUY" | "SELL"
    quantity: float
    price: float

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v.upper() not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        return v.upper()

    @field_validator("quantity", "price")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("must be positive")
        return v


class BulkGenerateRequest(BaseModel):
    count: int = 10


# ── Responses ──────────────────────────────────────────────────────────────────

class TradeAlertSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    risk_level: str
    combined_score: Optional[float] = None


class TradeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    trade_code: str
    trader_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    notional_value: float
    sector: Optional[str]
    timestamp: datetime
    source: str
    is_processed: bool
    alert: Optional[TradeAlertSummary] = None


class TradeListResponse(BaseModel):
    total: int
    trades: list[TradeResponse]
