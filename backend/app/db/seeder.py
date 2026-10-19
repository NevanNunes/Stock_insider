"""
app/db/seeder.py
─────────────────
Seeds the database from the pre-generated CSV files in data/:
  - symbols.csv     → Symbol table
  - traders.csv     → TraderAccount table
  - market_events.csv → MarketEvent table

Also creates default admin and trader user accounts if they don't exist.
Runs once at startup (idempotent — skips if data already present).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.market_event import MarketEvent
from app.models.symbol import Symbol
from app.models.trader_account import TraderAccount
from app.models.user import User

logger = logging.getLogger(__name__)


def seed_symbols(db: Session, data_dir: Path) -> None:
    if db.query(Symbol).count() > 0:
        return
    csv = data_dir / "symbols.csv"
    if not csv.exists():
        logger.warning("symbols.csv not found at %s", csv)
        return
    df = pd.read_csv(csv)
    for _, row in df.iterrows():
        db.add(Symbol(
            symbol=row["symbol"],
            company_name=row["company_name"],
            sector=row["sector"],
            baseline_price=float(row["baseline_price"]),
            volatility=float(row["volatility"]),
            average_daily_volume=float(row["average_daily_volume"]),
            typical_spread=float(row["typical_spread"]),
        ))
    db.commit()
    logger.info("Seeded %d symbols", df.shape[0])


def seed_traders(db: Session, data_dir: Path) -> None:
    if db.query(TraderAccount).count() > 0:
        return
    csv = data_dir / "traders.csv"
    if not csv.exists():
        logger.warning("traders.csv not found at %s", csv)
        return
    df = pd.read_csv(csv)
    for _, row in df.iterrows():
        db.add(TraderAccount(
            trader_id=row["trader_id"],
            trader_type=row["trader_type"],
            preferred_symbols=str(row.get("preferred_symbols", "")),
            preferred_sectors=str(row.get("preferred_sectors", "")),
            preferred_start_time=str(row.get("preferred_start_time", "")),
            preferred_end_time=str(row.get("preferred_end_time", "")),
            buy_probability=float(row.get("buy_probability", 0.5)),
            hist_mean_quantity=float(row.get("hist_mean_quantity", 0)) if pd.notna(row.get("hist_mean_quantity")) else None,
            hist_std_quantity=float(row.get("hist_std_quantity", 0)) if pd.notna(row.get("hist_std_quantity")) else None,
            hist_mean_notional=float(row.get("hist_mean_notional", 0)) if pd.notna(row.get("hist_mean_notional")) else None,
            hist_std_notional=float(row.get("hist_std_notional", 0)) if pd.notna(row.get("hist_std_notional")) else None,
            hist_trade_count=int(row.get("hist_trade_count", 0)),
            average_trade_quantity=float(row.get("average_trade_quantity", 100)),
            quantity_std=float(row.get("quantity_std", 20)),
            average_notional=float(row.get("average_notional", 100000)),
            notional_std=float(row.get("notional_std", 30000)),
            normal_trades_per_day=float(row.get("normal_trades_per_day", 3)),
        ))
    db.commit()
    logger.info("Seeded %d trader accounts", df.shape[0])


def seed_market_events(db: Session, data_dir: Path) -> None:
    if db.query(MarketEvent).count() > 0:
        return
    csv = data_dir / "market_events.csv"
    if not csv.exists():
        logger.warning("market_events.csv not found at %s", csv)
        return
    df = pd.read_csv(csv)  # columns: event_id, symbol, event_type, event_timestamp, event_severity, description
    for _, row in df.iterrows():
        try:
            event_time = pd.Timestamp(row["event_timestamp"])
            if event_time.tzinfo is None:
                event_time = event_time.tz_localize("Asia/Kolkata")
            event_time = event_time.to_pydatetime()
        except Exception:
            from datetime import datetime
            event_time = datetime.utcnow()

        db.add(MarketEvent(
            symbol=row["symbol"],
            event_type=row["event_type"],
            severity=row["event_severity"],
            description=str(row.get("description", "")),
            event_time=event_time,
        ))
    db.commit()
    logger.info("Seeded %d market events", df.shape[0])


def seed_default_users(db: Session) -> None:
    """Create default admin and trader accounts for the demo."""
    defaults = [
        {"username": "admin", "email": "admin@surveillance.local", "role": "admin", "password": "admin123"},
        {"username": "trader1", "email": "trader1@surveillance.local", "role": "trader", "password": "trader123"},
    ]
    for u in defaults:
        exists = db.query(User).filter(User.username == u["username"]).first()
        if not exists:
            db.add(User(
                username=u["username"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                is_active=True,
            ))
    db.commit()
    logger.info("Default users ready: admin / admin123  |  trader1 / trader123")


def run_all_seeds(db: Session) -> None:
    data_dir = settings.data_path
    logger.info("Running database seeder from: %s", data_dir)
    seed_symbols(db, data_dir)
    seed_traders(db, data_dir)
    seed_market_events(db, data_dir)
    seed_default_users(db)
    logger.info("Database seeding complete.")
