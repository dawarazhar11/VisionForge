"""
Pydantic schemas for trained model management.
"""
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ModelResponse(BaseModel):
    """Response schema for trained model information."""

    id: uuid.UUID = Field(..., description="Training job ID (used as model ID)")
    project_id: uuid.UUID = Field(..., description="Associated project ID")
    model_path: str = Field(..., description="Path to last model weights")
    best_model_path: Optional[str] = Field(None, description="Path to best model weights")

    # Model configuration
    model_size: str = Field(..., description="YOLO model variant (nano, small, etc.)")
    num_classes: int = Field(..., description="Number of classes trained")
    class_names: Optional[List[str]] = Field(None, description="Class names")

    # Training metrics
    metrics: Optional[Dict[str, float]] = Field(None, description="Validation metrics")
    epochs_completed: int = Field(..., description="Number of epochs completed")
    best_epoch: Optional[int] = Field(None, description="Epoch with best performance")
    training_time_seconds: float = Field(..., description="Total training time")

    # Metadata
    created_at: datetime = Field(..., description="Model creation timestamp")
    status: str = Field(..., description="Job status (SUCCESS, FAILED, etc.)")

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """Response schema for paginated model list."""

    models: List[ModelResponse]
    total: int = Field(..., description="Total number of models")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ModelExportRequest(BaseModel):
    """Request schema for model export."""

    format: str = Field(..., description="Export format (onnx, tflite, coreml, torchscript)")
    imgsz: int = Field(default=640, ge=320, le=1280, description="Input image size")
    optimize: bool = Field(default=True, description="Optimize for deployment")
    half: bool = Field(default=False, description="Use FP16 precision")
    int8: bool = Field(default=False, description="Use INT8 quantization")
    simplify: bool = Field(default=True, description="Simplify ONNX model")
    batch: int = Field(default=1, ge=1, le=32, description="Batch size")

    class Config:
        json_schema_extra = {
            "example": {
                "format": "onnx",
                "imgsz": 640,
                "optimize": True,
                "half": False,
                "simplify": True
            }
        }


class ModelExportResponse(BaseModel):
    """Response schema for model export."""

    success: bool = Field(..., description="Whether export succeeded")
    export_path: Optional[str] = Field(None, description="Path to exported model")
    format: str = Field(..., description="Export format used")
    file_size_mb: Optional[float] = Field(None, description="Exported file size in MB")
    error_message: Optional[str] = Field(None, description="Error message if failed")
