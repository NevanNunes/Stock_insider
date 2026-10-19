"""
app/anomaly_engine/isolation_forest.py
───────────────────────────────────────
Isolation Forest (scikit-learn) trained on the 11 leak-free behavioural features
from the historical dataset (feature_dataset.csv, dataset=="HISTORICAL" rows only).

The trained model is cached to disk (joblib) so it only needs one training pass.

Features used (matching the dataset spec — no ground-truth / retrospective cols):
  quantity, notional_value, trade_frequency_1h, trade_frequency_1d,
  buy_sell_ratio, time_deviation, volume_ratio, volume_deviation,
  price_return_before_trade, event_distance, trader_symbol_frequency

For a live manual trade, we estimate the missing features conservatively.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "if_model.joblib"

FEATURES = [
    "quantity",
    "notional_value",
    "trade_frequency_1h",
    "trade_frequency_1d",
    "buy_sell_ratio",
    "time_deviation",
    "volume_ratio",
    "volume_deviation",
    "price_return_before_trade",
    "event_distance",
    "trader_symbol_frequency",
]

# Feature defaults used when a live trade has no history yet
FEATURE_DEFAULTS = {
    "trade_frequency_1h": 1.0,
    "trade_frequency_1d": 3.0,
    "buy_sell_ratio": 1.0,
    "time_deviation": 0.0,
    "volume_ratio": 1.0,
    "volume_deviation": 0.0,
    "price_return_before_trade": 0.0,
    "event_distance": 99999.0,  # large = far from event = not suspicious
    "trader_symbol_frequency": 0.1,
}

_model = None  # module-level cache


def _load_or_train(data_dir: Path, contamination: float, random_state: int):
    """Load cached model from disk, or train from historical feature_dataset.csv."""
    global _model
    if _model is not None:
        return _model

    if MODEL_PATH.exists():
        logger.info("Loading cached Isolation Forest model from %s", MODEL_PATH)
        _model = joblib.load(MODEL_PATH)
        return _model

    # Train from scratch
    csv_path = data_dir / "feature_dataset.csv"
    if not csv_path.exists():
        logger.warning("feature_dataset.csv not found at %s — IF model will not be available", csv_path)
        return None

    logger.info("Training Isolation Forest from %s ...", csv_path)
    df = pd.read_csv(csv_path)
    hist = df[df["dataset"] == "HISTORICAL"].copy()

    missing = [f for f in FEATURES if f not in hist.columns]
    if missing:
        logger.warning("Missing features in dataset: %s — using defaults", missing)
        for f in missing:
            hist[f] = FEATURE_DEFAULTS.get(f, 0.0)

    X = hist[FEATURES].fillna(0.0).values

    from sklearn.ensemble import IsolationForest
    clf = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
    )
    clf.fit(X)
    joblib.dump(clf, MODEL_PATH)
    logger.info("Isolation Forest trained and saved to %s", MODEL_PATH)
    _model = clf
    return _model


def score_trade(
    quantity: float,
    notional_value: float,
    *,
    data_dir: Path,
    contamination: float = 0.05,
    random_state: int = 42,
    extra_features: Optional[dict] = None,
) -> float:
    """
    Return an anomaly score in [0, 1]:
      0.0 = perfectly normal
      1.0 = highly anomalous

    `extra_features` can supply optional contextual values; missing ones
    fall back to conservative defaults (not suspicious).
    """
    model = _load_or_train(data_dir, contamination, random_state)
    if model is None:
        return 0.5  # neutral if model unavailable

    feats = dict(FEATURE_DEFAULTS)
    feats.update(extra_features or {})
    feats["quantity"] = quantity
    feats["notional_value"] = notional_value

    row = np.array([[feats[f] for f in FEATURES]], dtype=float)

    # IsolationForest.score_samples → more negative = more anomalous
    raw = model.score_samples(row)[0]

    # Normalise to [0, 1]: typical range is roughly [-0.7, 0.0]
    # We clip and invert so higher = more anomalous
    normalised = float(np.clip((-raw) / 0.7, 0.0, 1.0))
    return round(normalised, 4)
