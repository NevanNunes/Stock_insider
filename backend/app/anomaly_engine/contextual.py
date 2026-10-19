"""
app/anomaly_engine/contextual.py
──────────────────────────────────
Contextual anomaly signals:
  1. Pre-event trading (trade within 24 h before a market event for the same symbol)
  2. Market volume spike (volume_ratio ≥ 2)
  3. Off-hours trading (time_deviation ≥ 60 min outside trader's preferred window)
  4. Rare-symbol trading (trader_symbol_frequency ≤ 1%)

Returns a 0–1 context_score and a flag list used in the explanation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.market_event import MarketEvent


PRE_EVENT_WINDOW_HOURS = 24    # look for events within 24 h of trade
PRE_EVENT_ALERT_HOURS = 24     # flag if trade is within 24 h before event
VOLUME_RATIO_THRESHOLD = 2.0
TIME_DEVIATION_THRESHOLD_MIN = 60.0
RARE_SYMBOL_THRESHOLD = 0.01   # ≤ 1% frequency


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _nearest_event_minutes(
    db: Session,
    symbol: str,
    timestamp: datetime,
) -> Optional[float]:
    """
    Return minutes to nearest scheduled market event for the symbol,
    searching ±24 h around the trade timestamp.
    Returns None if no events found.
    """
    ts_naive = _to_naive_utc(timestamp)
    window_start = ts_naive - timedelta(hours=PRE_EVENT_WINDOW_HOURS)
    window_end = ts_naive + timedelta(hours=PRE_EVENT_WINDOW_HOURS)

    events = (
        db.query(MarketEvent)
        .filter(
            MarketEvent.symbol == symbol,
            MarketEvent.event_time >= window_start,
            MarketEvent.event_time <= window_end,
        )
        .all()
    )
    if not events:
        return None

    distances = [
        abs((_to_naive_utc(e.event_time) - ts_naive).total_seconds() / 60.0)
        for e in events
    ]
    return min(distances)


def compute_context_score(
    db: Session,
    symbol: str,
    timestamp: datetime,
    *,
    time_deviation: float = 0.0,
    trader_symbol_frequency: float = 1.0,
    extra_features: Optional[dict] = None,
) -> dict:
    """
    Evaluate contextual anomaly signals.

    Returns:
      context_score        float 0–1
      is_pre_event         bool
      event_distance_min   float | None
      flags                list[str]  — human-readable reasons
    """
    extra = extra_features or {}
    volume_ratio: float = extra.get("volume_ratio", 1.0)

    flags: list[str] = []
    signal_score = 0.0

    # ── Signal 1: Pre-event activity ──────────────────────────────────────────
    event_dist = _nearest_event_minutes(db, symbol, timestamp)
    is_pre_event = False
    ts_naive = _to_naive_utc(timestamp)
    if event_dist is not None:
        event_timedelta = (
            db.query(MarketEvent)
            .filter(
                MarketEvent.symbol == symbol,
                MarketEvent.event_time >= ts_naive,
                MarketEvent.event_time <= ts_naive + timedelta(hours=PRE_EVENT_ALERT_HOURS),
            )
            .first()
        )
        if event_timedelta is not None:
            is_pre_event = True
            flags.append(
                f"Trade placed {event_dist:.0f} minutes before a scheduled market event"
                f" ({event_timedelta.event_type}) for {symbol}."
            )
            signal_score += 0.5

    # ── Signal 2: Market volume spike ─────────────────────────────────────────
    if volume_ratio >= VOLUME_RATIO_THRESHOLD:
        flags.append(
            f"Market volume for {symbol} is {volume_ratio:.1f}x the 20-day average"
            " (unusual activity in the market)."
        )
        signal_score += 0.25

    # ── Signal 3: Off-hours trading ───────────────────────────────────────────
    if time_deviation >= TIME_DEVIATION_THRESHOLD_MIN:
        flags.append(
            f"Trade occurred {time_deviation:.0f} minutes outside this trader's"
            " normal trading window."
        )
        signal_score += 0.25

    # ── Signal 4: Rare symbol ─────────────────────────────────────────────────
    if trader_symbol_frequency <= RARE_SYMBOL_THRESHOLD:
        pct = trader_symbol_frequency * 100
        flags.append(
            f"This trader has historically traded {symbol} only {pct:.1f}% of the time"
            " — significantly outside their usual preferences."
        )
        signal_score += 0.25

    context_score = round(min(signal_score, 1.0), 4)

    return {
        "context_score": context_score,
        "is_pre_event": is_pre_event,
        "event_distance_min": event_dist,
        "flags": flags,
    }
