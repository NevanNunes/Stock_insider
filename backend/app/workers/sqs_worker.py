"""
app/workers/sqs_worker.py
──────────────────────────
Background worker that continuously polls the queue (SQS or local),
runs anomaly detection on each dequeued trade, and broadcasts alerts.

Runs as an asyncio background task started at application startup.
Works identically offline (local asyncio.Queue) and on AWS (Amazon SQS).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timezone

from sqlalchemy.orm import Session

from app.anomaly_engine.detector import analyse_trade
from app.db.session import SessionLocal
from app.models.anomaly_alert import AnomalyAlert
from app.models.trade import Trade
from app.models.trader_account import TraderAccount
from app.services.notification_service import notify_high_risk_alert
from app.services.queue_service import dequeue_trade
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 0.5  # check queue every 500 ms


async def _process_message(message: dict) -> None:
    """Process a single queue message end-to-end."""
    trade_id: int = message.get("trade_id")
    trade_code: str = message.get("trade_code", "UNKNOWN")

    if not trade_id:
        logger.warning("Queue message missing trade_id: %s", message)
        return

    db: Session = SessionLocal()
    try:
        trade: Trade | None = db.query(Trade).filter(Trade.id == trade_id).first()
        if trade is None:
            logger.error("Trade id=%d not found in DB", trade_id)
            return

        trader: TraderAccount | None = (
            db.query(TraderAccount)
            .filter(TraderAccount.trader_id == trade.trader_id)
            .first()
        )
        if trader is None:
            logger.error("TraderAccount %s not found for trade %s", trade.trader_id, trade_code)
            return

        # ── Run anomaly detection ──────────────────────────────────────────────
        alert: AnomalyAlert = analyse_trade(trade, trader, db)

        # ── Persist alert ─────────────────────────────────────────────────────
        db.add(alert)
        trade.is_processed = True
        db.commit()
        db.refresh(alert)

        # ── Broadcast via WebSocket to connected admin clients ─────────────────
        alert_payload = {
            "event": "NEW_ALERT",
            "alert_id": alert.id,
            "trade_code": trade_code,
            "trader_id": trade.trader_id,
            "symbol": trade.symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "notional_value": trade.notional_value,
            "risk_level": alert.risk_level,
            "combined_score": alert.combined_score,
            "notional_zscore": alert.notional_zscore,
            "reason": alert.reason,
            "detected_at": alert.detected_at.isoformat(),
        }
        await ws_manager.broadcast_alert(alert_payload)

        # ── SNS notification for HIGH-risk trades ─────────────────────────────
        if alert.risk_level == "HIGH" and not alert.sns_notified:
            notify_high_risk_alert(
                trade_code=trade_code,
                trader_id=trade.trader_id,
                symbol=trade.symbol,
                risk_level=alert.risk_level,
                combined_score=alert.combined_score or 0.0,
                notional_z=alert.notional_zscore or 0.0,
                reason=alert.reason or "",
            )
            alert.sns_notified = True
            db.commit()

        logger.info(
            "Processed trade %s → alert #%d [%s] score=%.3f",
            trade_code, alert.id, alert.risk_level, alert.combined_score or 0,
        )

    except Exception as exc:
        logger.exception("Error processing trade %s: %s", trade_code, exc)
        db.rollback()
    finally:
        db.close()


async def run_worker() -> None:
    """
    Continuous polling loop.  Started as an asyncio background task.
    """
    logger.info("SQS Worker started — polling every %.1fs", POLL_INTERVAL_SECONDS)
    while True:
        try:
            message = await dequeue_trade()
            if message:
                await _process_message(message)
            else:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("SQS Worker shutting down gracefully.")
            break
        except Exception as exc:
            logger.exception("Unexpected worker error: %s", exc)
            await asyncio.sleep(2)  # back off on unexpected errors
