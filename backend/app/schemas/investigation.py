"""
app/schemas/investigation.py — Schemas for investigations
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OpenInvestigationRequest(BaseModel):
    alert_ids: list[int]
    notes: Optional[str] = None


class UpdateInvestigationRequest(BaseModel):
    status: Optional[str] = None    # OPEN | UNDER_REVIEW | CLOSED
    notes: Optional[str] = None


class InvestigationTradeSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    trade_code: str
    trader_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    notional_value: float
    timestamp: datetime


class InvestigationAlertSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    risk_level: str
    combined_score: Optional[float] = None
    notional_zscore: Optional[float] = None
    quantity_zscore: Optional[float] = None
    reason: Optional[str] = None
    detected_at: Optional[datetime] = None
    trade: Optional[InvestigationTradeSummary] = None


class InvestigationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    opened_by: int
    opened_by_username: Optional[str] = None
    status: str
    notes: Optional[str] = None
    report_url: Optional[str] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    alert_count: int = 0

    # Descriptive summary fields for immediate visibility
    title: Optional[str] = None
    primary_trader_id: Optional[str] = None
    primary_symbol: Optional[str] = None
    primary_trade_code: Optional[str] = None
    highest_risk_level: Optional[str] = None
    total_notional: Optional[float] = None
    summary_reason: Optional[str] = None

    alerts: list[InvestigationAlertSummary] = []

    @classmethod
    def from_orm_with_count(cls, inv) -> "InvestigationResponse":
        url = inv.report_url
        if url and url.startswith("file://"):
            url = f"http://localhost:8000/api/reports/{inv.id}/pdf"

        username = None
        if getattr(inv, "opened_by_user", None) and hasattr(inv.opened_by_user, "username"):
            username = inv.opened_by_user.username
        elif inv.opened_by == 1:
            username = "Admin"
        else:
            username = f"User #{inv.opened_by}"

        alerts_list: list[InvestigationAlertSummary] = []
        highest_risk = "LOW"
        risk_priority = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        traders: list[str] = []
        symbols: list[str] = []
        trade_codes: list[str] = []
        total_notional = 0.0
        primary_reason = ""

        inv_alerts = getattr(inv, "alerts", []) or []
        for a in inv_alerts:
            trade_obj = None
            if getattr(a, "trade", None):
                t = a.trade
                trade_obj = InvestigationTradeSummary(
                    id=t.id,
                    trade_code=t.trade_code,
                    trader_id=t.trader_id,
                    symbol=t.symbol,
                    side=t.side,
                    quantity=t.quantity,
                    price=t.price,
                    notional_value=t.notional_value,
                    timestamp=t.timestamp,
                )
                if t.trader_id and t.trader_id not in traders:
                    traders.append(t.trader_id)
                if t.symbol and t.symbol not in symbols:
                    symbols.append(t.symbol)
                if t.trade_code and t.trade_code not in trade_codes:
                    trade_codes.append(t.trade_code)
                total_notional += (t.notional_value or 0.0)

            if risk_priority.get(a.risk_level, 0) >= risk_priority.get(highest_risk, 0):
                highest_risk = a.risk_level

            if not primary_reason and a.reason:
                lines = [l.strip("- \r") for l in a.reason.split("\n") if l.strip().startswith("-")]
                if lines:
                    primary_reason = lines[0]
                else:
                    first_line = a.reason.split("\n")[0].strip()
                    if first_line:
                        primary_reason = first_line

            alerts_list.append(InvestigationAlertSummary(
                id=a.id,
                risk_level=a.risk_level,
                combined_score=a.combined_score,
                notional_zscore=a.notional_zscore,
                quantity_zscore=a.quantity_zscore,
                reason=a.reason,
                detected_at=a.detected_at,
                trade=trade_obj,
            ))

        primary_trader = traders[0] if traders else None
        primary_symbol = symbols[0] if symbols else None
        primary_code = trade_codes[0] if trade_codes else None

        title_parts = []
        if primary_trader:
            title_parts.append(primary_trader)
        if primary_symbol:
            title_parts.append(primary_symbol)
        if total_notional > 0:
            title_parts.append(f"${total_notional:,.0f}")

        case_title = " · ".join(title_parts) if title_parts else None

        return cls(
            id=inv.id,
            opened_by=inv.opened_by,
            opened_by_username=username,
            status=inv.status,
            notes=inv.notes,
            report_url=url,
            opened_at=inv.opened_at,
            closed_at=inv.closed_at,
            alert_count=len(inv_alerts),
            title=case_title,
            primary_trader_id=primary_trader,
            primary_symbol=primary_symbol,
            primary_trade_code=primary_code,
            highest_risk_level=highest_risk if inv_alerts else None,
            total_notional=total_notional if total_notional > 0 else None,
            summary_reason=primary_reason if primary_reason else None,
            alerts=alerts_list,
        )
