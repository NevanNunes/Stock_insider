"""
app/schemas/auth.py — Request/response schemas for authentication
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "trader"  # "trader" or "admin"
    trader_type: Optional[str] = "Diversified"
    expected_trade_size: Optional[float] = 100000.0
    preferred_sectors: Optional[str] = "IT;Finance"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    username: str
    trader_id: Optional[str] = None

