"""
Webhook Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class WebhookCreate(BaseModel):
    """Schema for creating a new webhook URL."""
    url: HttpUrl = Field(..., description="Webhook URL to receive notifications")
    description: Optional[str] = Field(None, max_length=255, description="Optional description of webhook purpose")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/webhook",
                "description": "Production webhook for job notifications"
            }
        }
    )


class WebhookUpdate(BaseModel):
    """Schema for updating an existing webhook."""
    url: Optional[HttpUrl] = Field(None, description="New webhook URL")
    description: Optional[str] = Field(None, max_length=255, description="Updated description")


class WebhookResponse(BaseModel):
    """Schema for webhook in API responses."""
    index: int = Field(..., description="Index in webhook_urls array")
    url: str = Field(..., description="Webhook URL")
    description: Optional[str] = Field(None, description="Webhook description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "index": 0,
                "url": "https://example.com/webhook",
                "description": "Production webhook"
            }
        }
    )


class WebhookListResponse(BaseModel):
    """Schema for list of webhooks."""
    webhooks: List[WebhookResponse] = Field(..., description="List of configured webhooks")
    total: int = Field(..., description="Total number of webhooks")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "webhooks": [
                    {"index": 0, "url": "https://example.com/webhook", "description": "Production"},
                    {"index": 1, "url": "https://staging.example.com/webhook", "description": "Staging"}
                ],
                "total": 2
            }
        }
    )


class WebhookTestRequest(BaseModel):
    """Schema for testing webhook delivery."""
    url: Optional[HttpUrl] = Field(None, description="Specific webhook URL to test (if not provided, tests all)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/webhook"
            }
        }
    )


class WebhookTestResponse(BaseModel):
    """Schema for webhook test results."""
    url: str = Field(..., description="Webhook URL that was tested")
    success: bool = Field(..., description="Whether webhook delivery succeeded")
    status_code: Optional[int] = Field(None, description="HTTP status code received")
    error: Optional[str] = Field(None, description="Error message if failed")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/webhook",
                "success": True,
                "status_code": 200,
                "response_time_ms": 145.3
            }
        }
    )
