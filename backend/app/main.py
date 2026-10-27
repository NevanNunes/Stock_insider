"""
app/main.py
────────────
FastAPI application factory.
Configures CORS, mounts all routers, starts the background SQS worker,
and runs the database seeder on first startup.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, auth, investigations, trades
from app.core.config import settings
from app.db.base import Base
from app.db.seeder import run_all_seeds
from app.db.session import SessionLocal, engine
import app.models  # Register all SQLAlchemy models before create_all()
from app.workers.sqs_worker import run_worker

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Application ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Cloud-Based Market Surveillance & Anomaly Detection API.\n\n"
        "**Academic prototype.** Uses synthetic data only. "
        "Alerts flag statistically unusual trades for human review — "
        "they do not constitute evidence of insider trading."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(trades.router)
app.include_router(alerts.router)
app.include_router(investigations.router)

# ── Direct WebSocket routes (matching both /api/ws/alerts and /ws/alerts) ───────
from app.api.alerts import alerts_websocket
app.add_api_websocket_route("/api/ws/alerts", alerts_websocket)
app.add_api_websocket_route("/ws/alerts", alerts_websocket)



# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health_check():
    """Used by ALB target group health checks."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "sqs_mode": "aws" if settings.use_sqs else "local",
        "sns_mode": "aws" if settings.use_sns else "local",
        "s3_mode": "aws" if settings.use_s3 else "local",
    }


# ── Symbols endpoint (for Trader Terminal dropdown) ────────────────────────────
from app.models.symbol import Symbol
from app.core.dependencies import get_db
from fastapi import Depends
from sqlalchemy.orm import Session


@app.get("/api/symbols", tags=["Reference Data"])
def list_symbols(db: Session = Depends(get_db)):
    """Returns all 20 fictional symbols for the Trader Terminal dropdown."""
    return db.query(Symbol).order_by(Symbol.symbol).all()


# ── Traders endpoint (for Trader Terminal dropdown) ────────────────────────────
from app.models.trader_account import TraderAccount


@app.get("/api/traders", tags=["Reference Data"])
def list_traders(db: Session = Depends(get_db)):
    """Returns all 50 trader profiles for the Trader Terminal dropdown."""
    traders = db.query(TraderAccount).order_by(TraderAccount.trader_id).all()
    return [
        {
            "trader_id": t.trader_id,
            "trader_type": t.trader_type,
            "avg_quantity": t.average_trade_quantity,
            "avg_notional": t.average_notional,
            "preferred_symbols": (t.preferred_symbols or "").split(";"),
        }
        for t in traders
    ]


# ── Startup / Shutdown ─────────────────────────────────────────────────────────
_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def on_startup():
    global _worker_task

    # 1. Create all DB tables (idempotent)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # 2. Seed reference data from CSV files
    db = SessionLocal()
    try:
        run_all_seeds(db)
    finally:
        db.close()

    # 3. Start the background SQS/anomaly worker
    _worker_task = asyncio.create_task(run_worker())
    logger.info("Background worker started.")


@app.on_event("shutdown")
async def on_shutdown():
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Application shutdown complete.")
