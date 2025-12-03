"""
Pydantic schemas for assembly projects.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project (used with file upload)."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating project metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Assembly Project",
                "description": "Modified description for mechanical component assembly"
            }
        }
    }


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: UUID
    user_id: UUID
    file_path: str
    file_size_mb: float
    file_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""
    projects: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
