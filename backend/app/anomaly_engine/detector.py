"""
app/anomaly_engine/detector.py
────────────────────────────────
Main anomaly detection orchestrator.

Pipeline for each incoming trade:
  1. Z-score (statistical): notional & quantity vs. trader's frozen historical baseline
  2. Isolation Forest (ML): 11-feature behavioural embedding
  3. Contextual: pre-event proximity, volume spike, off-hours, rare symbol

Composite score = 0.40 × stat + 0.40 × ml + 0.20 × context  (project-defined weights)

Risk classification:
  combined ≥ 0.65 → HIGH
  combined ≥ 0.35 → MEDIUM
  else            → LOW
(Z-score alone can also force HIGH if |z| ≥ 3.0 — see zscore.py)

All weights and thresholds are ACADEMIC / PROJECT-DEFINED, not regulatory standards.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.anomaly_engine.contextual import compute_context_score
from app.anomaly_engine.isolation_forest import score_trade as if_score
from app.anomaly_engine.zscore import compute_statistical_score
from app.core.config import settings
from app.models.anomaly_alert import AnomalyAlert
from app.models.trade import Trade
from app.models.trader_account import TraderAccount

logger = logging.getLogger(__name__)

# Composite thresholds
COMBINED_HIGH = 0.65
COMBINED_MEDIUM = 0.35


def _build_explanation(
    notional_z: float,
    quantity_z: float,
    stat_score: float,
    ml_score: float,
    ctx_result: dict,
    trader: TraderAccount,
    trade: Trade,
) -> str:
    """Build a human-readable explanation for display on the Admin Dashboard."""
    lines = [
        "Unusual trading activity detected. Further human review recommended.",
        "",
        "Trade flagged because:",
    ]

    if abs(notional_z) >= settings.Z_LOW_THRESHOLD:
        lines.append(
            f"- Notional value ₹{trade.notional_value:,.0f} is "
            f"{abs(notional_z):.1f}σ {'above' if notional_z > 0 else 'below'} "
            f"this trader's historical average (₹{trader.hist_mean_notional:,.0f})."
        )

    if abs(quantity_z) >= settings.Z_LOW_THRESHOLD:
        lines.append(
            f"- Quantity {trade.quantity:,.0f} shares is "
            f"{abs(quantity_z):.1f}σ {'above' if quantity_z > 0 else 'below'} "
            f"this trader's historical average ({trader.hist_mean_quantity:,.0f} shares)."
        )

    if ml_score > 0.6:
        lines.append(
            f"- Multi-feature machine learning (Isolation Forest) score: {ml_score:.2f}/1.00 "
            f"(≥0.6 is flagged as behaviorally unusual)."
        )

    for flag in ctx_result.get("flags", []):
        lines.append(f"- {flag}")

    if len(lines) == 3:
        lines.append("- Composite anomaly score exceeded detection threshold.")

    return "\n".join(lines)


def _final_risk(stat_result: dict, combined: float) -> str:
    """
    Final risk level:
    - Always respect HIGH from Z-score (|z| ≥ 3.0)
    - Otherwise classify by combined score
    """
    if stat_result["risk_level_stat"] == "HIGH":
        return "HIGH"
    if combined >= COMBINED_HIGH:
        return "HIGH"
    if combined >= COMBINED_MEDIUM:
        return "MEDIUM"
    return "LOW"


def analyse_trade(
    trade: Trade,
    trader: TraderAccount,
    db: Session,
    extra_features: Optional[dict] = None,
) -> AnomalyAlert:
    """
    Run the full anomaly detection pipeline on a single Trade.

    Returns an AnomalyAlert instance (not yet committed to DB — caller commits).
    """
    extra = extra_features or {}

    # ── 1. Statistical (Z-score) ──────────────────────────────────────────────
    stat_result = compute_statistical_score(
        notional_value=trade.notional_value,
        quantity=trade.quantity,
        hist_mean_notional=trader.hist_mean_notional,
        hist_std_notional=trader.hist_std_notional,
        hist_mean_quantity=trader.hist_mean_quantity,
        hist_std_quantity=trader.hist_std_quantity,
    )

    # ── 2. Machine Learning (Isolation Forest) ────────────────────────────────
    ml_anomaly_score = if_score(
        quantity=trade.quantity,
        notional_value=trade.notional_value,
        data_dir=settings.data_path,
        contamination=settings.IF_CONTAMINATION,
        random_state=settings.IF_RANDOM_STATE,
        extra_features=extra,
    )

    # ── 3. Contextual ─────────────────────────────────────────────────────────
    ctx_result = compute_context_score(
        db=db,
        symbol=trade.symbol,
        timestamp=trade.timestamp if trade.timestamp.tzinfo else trade.timestamp.replace(tzinfo=timezone.utc),
        time_deviation=extra.get("time_deviation", 0.0),
        trader_symbol_frequency=extra.get("trader_symbol_frequency", 1.0),
        extra_features=extra,
    )

    # ── 4. Composite score ────────────────────────────────────────────────────
    combined = (
        settings.W_STAT * stat_result["statistical_score"]
        + settings.W_ML * ml_anomaly_score
        + settings.W_CTX * ctx_result["context_score"]
    )
    combined = round(combined, 4)

    # ── 5. Risk classification ────────────────────────────────────────────────
    risk_level = _final_risk(stat_result, combined)

    # ── 6. Human-readable explanation ─────────────────────────────────────────
    reason = _build_explanation(
        stat_result["notional_zscore"],
        stat_result["quantity_zscore"],
        stat_result["statistical_score"],
        ml_anomaly_score,
        ctx_result,
        trader,
        trade,
    )

    alert = AnomalyAlert(
        trade_id=trade.id,
        notional_zscore=stat_result["notional_zscore"],
        quantity_zscore=stat_result["quantity_zscore"],
        statistical_score=stat_result["statistical_score"],
        ml_score=ml_anomaly_score,
        context_score=ctx_result["context_score"],
        combined_score=combined,
        risk_level=risk_level,
        reason=reason,
        status="OPEN",
        sns_notified=False,
    )

    logger.info(
        "Trade %s | notional_z=%.2f | ml=%.2f | ctx=%.2f | combined=%.2f | risk=%s",
        trade.trade_code,
        stat_result["notional_zscore"],
        ml_anomaly_score,
        ctx_result["context_score"],
        combined,
        risk_level,
    )

    return alert
