"""
app/api/trades.py
──────────────────
Trade API endpoints:
  POST /api/trades                   — Manual trade from Trader Terminal
  POST /api/trades/generate-suspicious — 1-click random suspicious trade
  POST /api/trades/generate-normal   — 1-click normal baseline trade
  POST /api/trades/generate          — Bulk trade generation (seeded)
  GET  /api/trades                   — List & filter trades
  GET  /api/trades/{id}              — Trade detail
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.symbol import Symbol
from app.models.trade import Trade
from app.models.trader_account import TraderAccount
from app.models.user import User
from app.schemas.trade import (
    BulkGenerateRequest,
    ManualTradeRequest,
    TradeListResponse,
    TradeResponse,
)
from app.services.queue_service import enqueue_trade

router = APIRouter(prefix="/api/trades", tags=["Trades"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_trade_code(trader_id: str, db: Session) -> str:
    count = db.query(Trade).filter(Trade.trader_id == trader_id).count() + 1
    return f"{trader_id}-{count:06d}"


async def _create_and_enqueue(trade: Trade, db: Session) -> Trade:
    """Persist trade to DB then push onto the processing queue."""
    db.add(trade)
    db.commit()
    db.refresh(trade)
    await enqueue_trade(trade.id, trade.trade_code)
    return trade


def _get_trader_or_404(trader_id: str, db: Session) -> TraderAccount:
    trader = db.query(TraderAccount).filter(TraderAccount.trader_id == trader_id).first()
    if not trader:
        raise HTTPException(status_code=404, detail=f"Trader {trader_id!r} not found")
    return trader


def _get_symbol_or_404(symbol: str, db: Session) -> Symbol:
    sym = db.query(Symbol).filter(Symbol.symbol == symbol).first()
    if not sym:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol!r} not found")
    return sym


# ── Manual trade entry ────────────────────────────────────────────────────────

@router.post("", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def submit_manual_trade(
    payload: ManualTradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trader Terminal — manual trade submission.
    Any authenticated user (trader or admin) can submit.
    """
    trader = _get_trader_or_404(payload.trader_id, db)
    sym = _get_symbol_or_404(payload.symbol, db)

    notional = round(payload.quantity * payload.price, 2)
    trade = Trade(
        trade_code=_make_trade_code(payload.trader_id, db),
        trader_id=payload.trader_id,
        symbol=payload.symbol,
        side=payload.side,
        quantity=payload.quantity,
        price=payload.price,
        notional_value=notional,
        sector=sym.sector,
        timestamp=datetime.now(timezone.utc),
        is_synthetic=True,
        source="MANUAL",
        is_processed=False,
    )
    return await _create_and_enqueue(trade, db)


# ── 1-Click suspicious trade ──────────────────────────────────────────────────

@router.post("/generate-suspicious", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def generate_suspicious_trade(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    1-Click: generate and immediately submit one realistic suspicious trade.
    Randomly picks an anomaly archetype (LARGE_TRADE, PRE_EVENT_ACTIVITY,
    UNUSUAL_TIME, FREQUENCY_SPIKE, BEHAVIOR_CHANGE) and crafts a trade
    that will trigger a HIGH-risk alert.
    """
    # Pick a random conservative trader (small baseline makes anomaly obvious)
    conservative_traders = (
        db.query(TraderAccount)
        .filter(TraderAccount.trader_type == "Conservative")
        .all()
    )
    traders = conservative_traders or db.query(TraderAccount).all()
    trader = random.choice(traders)

    # Pick a high-priced symbol for maximum notional impact
    symbols = db.query(Symbol).order_by(Symbol.baseline_price.desc()).limit(5).all()
    sym = random.choice(symbols) if symbols else db.query(Symbol).first()

    if not sym:
        raise HTTPException(status_code=503, detail="No symbols in DB — run the seeder first")

    # Anomaly: 6-10× the trader's normal quantity
    multiplier = random.uniform(6, 10)
    qty = round((trader.average_trade_quantity or 100) * multiplier)
    price = round(sym.baseline_price * random.uniform(0.99, 1.01), 2)
    notional = round(qty * price, 2)

    trade = Trade(
        trade_code=_make_trade_code(trader.trader_id, db),
        trader_id=trader.trader_id,
        symbol=sym.symbol,
        side="BUY",
        quantity=qty,
        price=price,
        notional_value=notional,
        sector=sym.sector,
        timestamp=datetime.now(timezone.utc),
        is_synthetic=True,
        source="RANDOM_SUSPICIOUS",
        is_processed=False,
    )
    return await _create_and_enqueue(trade, db)


# ── 1-Click normal trade ──────────────────────────────────────────────────────

@router.post("/generate-normal", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def generate_normal_trade(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    1-Click: generate one fully normal baseline trade (will score LOW risk).
    """
    trader = random.choice(db.query(TraderAccount).all())
    preferred = (trader.preferred_symbols or "").split(";")
    sym_code = random.choice([s for s in preferred if s]) if preferred else None

    sym = None
    if sym_code:
        sym = db.query(Symbol).filter(Symbol.symbol == sym_code.strip()).first()
    if not sym:
        sym = db.query(Symbol).first()
    if not sym:
        raise HTTPException(status_code=503, detail="No symbols in DB — run the seeder first")

    # Normal: within 0.8–1.2× historical average
    qty = round((trader.average_trade_quantity or 100) * random.uniform(0.8, 1.2))
    price = round(sym.baseline_price * random.uniform(0.98, 1.02), 2)
    notional = round(qty * price, 2)

    trade = Trade(
        trade_code=_make_trade_code(trader.trader_id, db),
        trader_id=trader.trader_id,
        symbol=sym.symbol,
        side=random.choice(["BUY", "SELL"]),
        quantity=qty,
        price=price,
        notional_value=notional,
        sector=sym.sector,
        timestamp=datetime.now(timezone.utc),
        is_synthetic=True,
        source="RANDOM_NORMAL",
        is_processed=False,
    )
    return await _create_and_enqueue(trade, db)


# ── Bulk generation ───────────────────────────────────────────────────────────

@router.post("/generate", response_model=dict)
async def bulk_generate_trades(
    payload: BulkGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk generate N normal + a few suspicious trades (for seeding the demo DB)."""
    traders = db.query(TraderAccount).all()
    symbols = db.query(Symbol).all()

    if not traders or not symbols:
        raise HTTPException(status_code=503, detail="Run the seeder first")

    count = min(payload.count, 200)  # cap for safety
    queued = 0

    for _ in range(count):
        trader = random.choice(traders)
        sym = random.choice(symbols)
        qty = round((trader.average_trade_quantity or 100) * random.uniform(0.7, 1.3))
        price = round(sym.baseline_price * random.uniform(0.97, 1.03), 2)

        trade = Trade(
            trade_code=_make_trade_code(trader.trader_id, db),
            trader_id=trader.trader_id,
            symbol=sym.symbol,
            side=random.choice(["BUY", "SELL"]),
            quantity=qty,
            price=price,
            notional_value=round(qty * price, 2),
            sector=sym.sector,
            timestamp=datetime.now(timezone.utc),
            is_synthetic=True,
            source="BULK_GENERATED",
            is_processed=False,
        )
        db.add(trade)
        db.flush()
        await enqueue_trade(trade.id, trade.trade_code)
        queued += 1

    db.commit()
    return {"queued": queued, "message": f"{queued} trades queued for anomaly processing"}


# ── List & filter ─────────────────────────────────────────────────────────────

@router.get("", response_model=TradeListResponse)
def list_trades(
    trader_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Trade)
    if trader_id:
        q = q.filter(Trade.trader_id == trader_id)
    if symbol:
        q = q.filter(Trade.symbol == symbol)
    if side:
        q = q.filter(Trade.side == side.upper())
    total = q.count()
    trades = q.order_by(Trade.timestamp.desc()).offset(skip).limit(limit).all()
    return TradeListResponse(total=total, trades=trades)


@router.get("/{trade_id}", response_model=TradeResponse)
def get_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade
