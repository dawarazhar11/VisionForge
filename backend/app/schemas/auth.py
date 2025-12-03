"""
Authentication Pydantic schemas.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT token."""
    user_id: Optional[str] = None


class UserLogin(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str
