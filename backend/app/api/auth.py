"""
app/api/auth.py — Authentication endpoints
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
import re
from app.core.security import create_access_token, hash_password, verify_password
from app.models.trader_account import TraderAccount
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/me", response_model=TokenResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's profile including their linked trader_id."""
    token = create_access_token({"sub": str(current_user.id), "role": current_user.role})
    return TokenResponse(
        access_token=token,
        role=current_user.role,
        user_id=current_user.id,
        username=current_user.username,
        trader_id=current_user.trader_id,  # stamped at registration / backfill
    )

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    If registering as a trader, automatically provisions a TraderAccount profile
    with an initialized baseline to support anomaly detection from day 1.
    """
    # 1. Validate uniqueness
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 2. Create User
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role if payload.role in ("admin", "trader") else "trader",
        is_active=True,
    )
    db.add(user)
    db.flush()  # to obtain user.id

    new_trader_id = None
    if user.role == "trader":
        # Determine next TRDxxx ID
        all_traders = db.query(TraderAccount.trader_id).all()
        max_num = 0
        for (tid,) in all_traders:
            match = re.search(r"TRD(\d+)", tid)
            if match:
                max_num = max(max_num, int(match.group(1)))
        next_num = max_num + 1
        new_trader_id = f"TRD{next_num:03d}"

        archetype = payload.trader_type or "Diversified"
        exp_notional = max(1000.0, float(payload.expected_trade_size or 100000.0))
        notional_std = exp_notional * 0.3
        avg_qty = max(10.0, round(exp_notional / 500.0))
        qty_std = round(avg_qty * 0.25)

        trader_profile = TraderAccount(
            trader_id=new_trader_id,
            user_id=user.id,
            trader_type=archetype,
            preferred_symbols="",
            preferred_sectors=payload.preferred_sectors or "IT;Finance",
            preferred_start_time="09:15",
            preferred_end_time="15:30",
            buy_probability=0.5,
            hist_mean_quantity=float(avg_qty),
            hist_std_quantity=float(qty_std),
            hist_mean_notional=float(exp_notional),
            hist_std_notional=float(notional_std),
            hist_trade_count=1,
            average_trade_quantity=float(avg_qty),
            quantity_std=float(qty_std),
            average_notional=float(exp_notional),
            notional_std=float(notional_std),
            normal_trades_per_day=3.0,
        )
    user.trader_id = new_trader_id   # authoritative link on the User row
    db.add(trader_profile)

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        username=user.username,
        trader_id=new_trader_id,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT token.
    The token payload includes the user's role (admin or trader)
    so the frontend can route to the correct portal.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    token = create_access_token({"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        username=user.username,
        trader_id=user.trader_id,   # read directly from User — no FK lookup needed
    )

