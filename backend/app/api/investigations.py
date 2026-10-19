"""
app/api/investigations.py
──────────────────────────
Investigation & report endpoints:
  POST  /api/investigations              — Open investigation
  GET   /api/investigations              — List all investigations
  GET   /api/investigations/{id}         — Detail
  PATCH /api/investigations/{id}         — Update status/notes
  GET   /api/reports/{investigation_id}  — Generate + return/upload PDF report
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, get_db, require_admin
from app.models.anomaly_alert import AnomalyAlert
from app.models.investigation import Investigation
from app.models.user import User
from app.schemas.investigation import (
    InvestigationResponse,
    OpenInvestigationRequest,
    UpdateInvestigationRequest,
)
from app.services.report_service import generate_pdf_report, save_report

router = APIRouter(prefix="/api", tags=["Investigations & Reports"])


@router.post("/investigations", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def open_investigation(
    payload: OpenInvestigationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Open an investigation on one or more alerts."""
    inv = Investigation(
        opened_by=current_user.id,
        status="OPEN",
        notes=payload.notes,
    )
    db.add(inv)
    db.flush()

    # Link alerts to this investigation
    alerts = db.query(AnomalyAlert).filter(AnomalyAlert.id.in_(payload.alert_ids)).all()
    for alert in alerts:
        alert.investigation_id = inv.id
        alert.status = "UNDER_REVIEW"

    db.commit()
    db.refresh(inv)
    return InvestigationResponse.from_orm_with_count(inv)


@router.get("/investigations", response_model=list[InvestigationResponse])
def list_investigations(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Investigation).options(joinedload(Investigation.alerts))
    if status:
        q = q.filter(Investigation.status == status.upper())
    invs = q.order_by(Investigation.opened_at.desc()).offset(skip).limit(limit).all()
    return [InvestigationResponse.from_orm_with_count(i) for i in invs]


@router.get("/investigations/{inv_id}", response_model=InvestigationResponse)
def get_investigation(
    inv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.alerts))
        .filter(Investigation.id == inv_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return InvestigationResponse.from_orm_with_count(inv)


@router.patch("/investigations/{inv_id}", response_model=InvestigationResponse)
def update_investigation(
    inv_id: int,
    payload: UpdateInvestigationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    inv = db.query(Investigation).filter(Investigation.id == inv_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if payload.status:
        inv.status = payload.status.upper()
        if payload.status.upper() == "CLOSED":
            inv.closed_at = datetime.now(timezone.utc)
            for alert in inv.alerts:
                alert.status = "CLOSED"
    if payload.notes is not None:
        inv.notes = payload.notes

    db.commit()
    db.refresh(inv)
    return InvestigationResponse.from_orm_with_count(inv)


@router.get("/reports/{inv_id}")
def generate_report(
    inv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Generate a PDF compliance report for an investigation.
    Saves to S3 (production) or local disk (development).
    Returns JSON with the URL, or streams PDF if client requests it.
    """
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.alerts).joinedload(AnomalyAlert.trade))
        .filter(Investigation.id == inv_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    pdf_bytes = generate_pdf_report(
        investigation_id=inv.id,
        alerts=inv.alerts,
        notes=inv.notes or "",
        opened_by=current_user.username,
    )

    s3_key, url = save_report(inv.id, pdf_bytes)
    inv.report_s3_key = s3_key
    inv.report_url = url
    db.commit()

    return {"investigation_id": inv_id, "report_url": url, "s3_key": s3_key}
