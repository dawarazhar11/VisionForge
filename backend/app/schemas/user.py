"""
User Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "engineer@yolovision.com",
                "password": "SecurePass123!",
                "full_name": "Jane Engineer"
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    """User schema as stored in database."""
    id: UUID
    is_active: bool
    is_superuser: bool
    storage_quota_mb: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """User schema for API responses (without sensitive data)."""
    id: UUID
    is_active: bool
    storage_quota_mb: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
