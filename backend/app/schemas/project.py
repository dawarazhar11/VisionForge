"""
Pydantic schemas for assembly projects.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
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
    class_map: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Object→class mapping used when rendering this project. Either a "
            "plain {object_name: class_index} dict, or "
            "{'object_to_class': {...}, 'class_names': [...]}."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Assembly Project",
                "description": "Modified description for mechanical component assembly",
                "class_map": {
                    "object_to_class": {"gear_housing": 0, "shaft": 1},
                    "class_names": ["housing", "shaft"]
                }
            }
        }
    }


class ProjectClassMapResponse(BaseModel):
    """Schema for a project's resolved class map."""
    project_id: UUID
    object_to_class: Dict[str, int]
    class_names: List[str]
    source: str


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


class PartFeatureResponse(BaseModel):
    """Schema for a single recognized manufacturing feature."""
    id: UUID
    feature_type: str
    class_index: int
    center: List[float]
    normal: List[float]
    radius: Optional[float] = None
    depth: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    properties: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class PartFeatureListResponse(BaseModel):
    """Schema for project feature list response."""
    project_id: UUID
    features: List[PartFeatureResponse]
    total: int
    class_names: List[str]
