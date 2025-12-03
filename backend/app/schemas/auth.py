"""
Authentication Pydantic schemas.
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5YTg3Zjc1ZC0zYjhlLTRhNmMtOGJiYi1lYjg5ZTcwOTUxOGUiLCJleHAiOjE3MzYyODQzODB9.example",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5YTg3Zjc1ZC0zYjhlLTRhNmMtOGJiYi1lYjg5ZTcwOTUxOGUiLCJleHAiOjE3MzkyNzYzODB9.example",
                "token_type": "bearer"
            }
        }
    )


class TokenData(BaseModel):
    """Data encoded in JWT token."""
    user_id: Optional[str] = None


class UserLogin(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "engineer@yolovision.com",
                "password": "SecurePass123!"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5YTg3Zjc1ZC0zYjhlLTRhNmMtOGJiYi1lYjg5ZTcwOTUxOGUiLCJleHAiOjE3MzkyNzYzODB9.example"
            }
        }
    )
