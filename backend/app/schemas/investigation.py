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


class InvestigationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    opened_by: int
    status: str
    notes: Optional[str]
    report_url: Optional[str]
    opened_at: datetime
    closed_at: Optional[datetime]
    alert_count: int = 0

    @classmethod
    def from_orm_with_count(cls, inv) -> "InvestigationResponse":
        url = inv.report_url
        if url and url.startswith("file://"):
            url = f"http://localhost:8000/api/reports/{inv.id}/pdf"
        return cls(
            id=inv.id,
            opened_by=inv.opened_by,
            status=inv.status,
            notes=inv.notes,
            report_url=url,
            opened_at=inv.opened_at,
            closed_at=inv.closed_at,
            alert_count=len(inv.alerts),
        )
