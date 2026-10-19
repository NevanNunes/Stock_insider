"""
app/anomaly_engine/zscore.py
──────────────────────────────
Trader-specific Z-score calculation.

Z = (current_value - trader_historical_mean) / trader_historical_std

Uses the frozen historical baseline stored in TraderAccount (hist_mean_*, hist_std_*)
to avoid data leakage — test trades never influence the baseline.

Risk thresholds (project-defined, NOT regulatory standards):
  |Z| < 2.0  → LOW
  2.0 ≤ |Z| < 3.0 → MEDIUM
  |Z| ≥ 3.0  → HIGH
"""
from __future__ import annotations

import math
from typing import Optional

from app.core.config import settings


MIN_STD = 1e-6  # avoid division by zero


def compute_zscore(value: float, mean: float, std: float) -> float:
    """Return Z-score; returns 0.0 if std is effectively zero."""
    if std is None or std < MIN_STD:
        return 0.0
    return (value - mean) / std


def zscore_to_01(z: float) -> float:
    """
    Convert an absolute Z-score to a 0–1 anomaly signal using a sigmoid-like
    mapping.  z=0 → 0.0; z=2 → ~0.5; z=3 → ~0.75; z≥5 → ~1.0.
    """
    return 1.0 - math.exp(-max(abs(z), 0.0) / 3.0)


def classify_risk(notional_z: float, quantity_z: float) -> str:
    """
    Map Z-scores to risk level using project-defined thresholds.
    Any |z| ≥ 4.0 upgrades to HIGH regardless.
    """
    max_z = max(abs(notional_z), abs(quantity_z))
    if max_z >= settings.Z_HIGH_THRESHOLD or max_z >= 4.0:
        return "HIGH"
    if max_z >= settings.Z_LOW_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def compute_statistical_score(
    notional_value: float,
    quantity: float,
    hist_mean_notional: Optional[float],
    hist_std_notional: Optional[float],
    hist_mean_quantity: Optional[float],
    hist_std_quantity: Optional[float],
) -> dict:
    """
    Compute Z-scores and the combined 0–1 statistical anomaly score.

    Returns a dict with keys:
      notional_zscore, quantity_zscore, statistical_score, risk_level_stat
    """
    nz = compute_zscore(
        notional_value,
        hist_mean_notional or notional_value,
        hist_std_notional or 0.0,
    )
    qz = compute_zscore(
        quantity,
        hist_mean_quantity or quantity,
        hist_std_quantity or 0.0,
    )

    # Take the max absolute signal as the composite score
    stat_score = max(zscore_to_01(nz), zscore_to_01(qz))

    return {
        "notional_zscore": round(nz, 4),
        "quantity_zscore": round(qz, 4),
        "statistical_score": round(stat_score, 4),
        "risk_level_stat": classify_risk(nz, qz),
    }
