"""
app/api/alerts.py
──────────────────
Alert endpoints:
  GET /api/alerts          — List & filter
  GET /api/alerts/latest   — Polling fallback (returns alerts since a given id)
  GET /api/alerts/{id}     — Alert detail
  WS  /ws/alerts           — Real-time WebSocket stream
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, get_db
from app.models.anomaly_alert import AnomalyAlert
from app.models.user import User
from app.schemas.alert import AlertLatestResponse, AlertListResponse, AlertResponse
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["Alerts"])


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/api/alerts", response_model=AlertListResponse)
def list_alerts(
    risk_level: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH"),
    status: Optional[str] = Query(None, description="OPEN | UNDER_REVIEW | CLOSED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AnomalyAlert).options(joinedload(AnomalyAlert.trade))
    if risk_level:
        q = q.filter(AnomalyAlert.risk_level == risk_level.upper())
    if status:
        q = q.filter(AnomalyAlert.status == status.upper())
    total = q.count()
    alerts = q.order_by(AnomalyAlert.detected_at.desc()).offset(skip).limit(limit).all()
    return AlertListResponse(total=total, alerts=alerts)


@router.get("/api/alerts/latest", response_model=AlertLatestResponse)
def latest_alerts(
    since_id: int = Query(0, description="Return alerts with id > since_id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Short-polling fallback for clients that can't use WebSockets.
    Frontend calls this every 2 s with the highest alert id it has seen.
    Returns only NEW alerts since then.
    """
    alerts = (
        db.query(AnomalyAlert)
        .options(joinedload(AnomalyAlert.trade))
        .filter(AnomalyAlert.id > since_id)
        .order_by(AnomalyAlert.detected_at.desc())
        .limit(20)
        .all()
    )
    newest_id = alerts[0].id if alerts else since_id
    return AlertLatestResponse(alerts=alerts, newest_id=newest_id)


@router.get("/api/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = (
        db.query(AnomalyAlert)
        .options(joinedload(AnomalyAlert.trade))
        .filter(AnomalyAlert.id == alert_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """
    Real-time alert stream for Admin Dashboard.
    Connect with:  ws://localhost:8000/ws/alerts?token=<JWT>
    On connection, sends a 'CONNECTED' handshake.
    Receives 'NEW_ALERT' events pushed by the SQS worker whenever
    a trade is flagged.
    """
    await ws_manager.connect(websocket)
    try:
        # Send connection acknowledgement
        await websocket.send_json({
            "event": "CONNECTED",
            "message": "Market Surveillance WebSocket connected. Awaiting alerts...",
            "active_connections": ws_manager.connection_count,
        })

        # Keep connection alive — client can send pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)
