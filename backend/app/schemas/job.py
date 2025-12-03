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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "job_type": "test",
                    "config": {"message": "Testing Celery integration"}
                },
                {
                    "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "job_type": "render",
                    "config": {"num_images": 100, "resolution": "1920x1080"}
                },
                {
                    "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "job_type": "train",
                    "config": {"epochs": 50, "batch_size": 16, "model": "yolov8n"}
                }
            ]
        }
    }


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
