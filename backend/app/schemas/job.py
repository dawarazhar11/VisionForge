"""
Pydantic schemas for training jobs.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    project_id: UUID = Field(..., description="Project ID to process")
    job_type: str = Field(..., description="Type of job (test, render, train)")
    config: Optional[Dict[str, Any]] = Field(None, description="Job configuration")


class JobResponse(BaseModel):
    """Schema for job response."""
    id: UUID
    project_id: UUID
    status: str
    progress: int
    stage: Optional[str] = None  # job_type is stored in stage field
    config_json: Optional[Dict[str, Any]] = None
    dataset_path: Optional[str] = None
    metrics_json: Optional[Dict[str, Any]] = None  # Contains celery_task_id and results
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for paginated job list."""
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
