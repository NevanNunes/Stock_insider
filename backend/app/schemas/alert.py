"""
app/schemas/alert.py — Request/response schemas for anomaly alerts
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.trade import TradeResponse


class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    trade_id: int
    trade: Optional[TradeResponse] = None
    notional_zscore: Optional[float]
    quantity_zscore: Optional[float]
    statistical_score: Optional[float]
    ml_score: Optional[float]
    context_score: Optional[float]
    combined_score: Optional[float]
    risk_level: str
    reason: Optional[str]
    status: str
    detected_at: datetime
    sns_notified: bool
    investigation_id: Optional[int]


class AlertListResponse(BaseModel):
    total: int
    alerts: list[AlertResponse]


class AlertLatestResponse(BaseModel):
    """For the short-polling fallback endpoint."""
    alerts: list[AlertResponse]
    newest_id: Optional[int]
