"""
YOLO training configuration schemas and constants.
"""
from typing import Dict, Optional, List
from enum import Enum
from pydantic import BaseModel, Field


# Default model variants
class YOLOModelSize(str, Enum):
    """YOLO model size variants."""
    NANO = "yolo11n-seg.pt"  # Fastest, smallest
    SMALL = "yolo11s-seg.pt"  # Balanced
    MEDIUM = "yolo11m-seg.pt"  # Better accuracy
    LARGE = "yolo11l-seg.pt"  # High accuracy
    XLARGE = "yolo11x-seg.pt"  # Best accuracy


class ExportFormat(str, Enum):
    """Model export formats."""
    PYTORCH = "pt"
    ONNX = "onnx"
    TFLITE = "tflite"
    COREML = "coreml"
    TORCHSCRIPT = "torchscript"


# Default training parameters
DEFAULT_TRAINING_PARAMS = {
    "epochs": 50,
    "batch_size": 16,
    "imgsz": 640,
    "device": "0",  # GPU 0
    "workers": 8,
    "patience": 10,
    "save_period": 5,
}


class YOLOTrainingConfig(BaseModel):
    """Configuration for YOLO model training."""

    # Model configuration
    model: YOLOModelSize = Field(
        default=YOLOModelSize.NANO,
        description="YOLO model variant to train"
    )

    pretrained: bool = Field(
        default=True,
        description="Use pretrained weights for transfer learning"
    )

    # Training hyperparameters
    epochs: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Number of training epochs"
    )

    batch_size: int = Field(
        default=16,
        ge=1,
        le=128,
        description="Batch size for training"
    )

    imgsz: int = Field(
        default=640,
        ge=320,
        le=1280,
        description="Input image size (square)"
    )

    # Optimization
    optimizer: str = Field(
        default="AdamW",
        description="Optimizer (SGD, Adam, AdamW, etc.)"
    )

    lr0: float = Field(
        default=0.01,
        ge=0.0001,
        le=1.0,
        description="Initial learning rate"
    )

    lrf: float = Field(
        default=0.01,
        ge=0.0001,
        le=1.0,
        description="Final learning rate factor"
    )

    momentum: float = Field(
        default=0.937,
        ge=0.0,
        le=1.0,
        description="SGD momentum/Adam beta1"
    )

    weight_decay: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.1,
        description="Optimizer weight decay"
    )

    # Data augmentation
    augment: bool = Field(
        default=True,
        description="Enable data augmentation"
    )

    hsv_h: float = Field(
        default=0.015,
        ge=0.0,
        le=1.0,
        description="HSV-Hue augmentation"
    )

    hsv_s: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="HSV-Saturation augmentation"
    )

    hsv_v: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="HSV-Value augmentation"
    )

    degrees: float = Field(
        default=0.0,
        ge=0.0,
        le=180.0,
        description="Rotation augmentation (degrees)"
    )

    translate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Translation augmentation"
    )

    scale: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Scale augmentation"
    )

    flipud: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Vertical flip probability"
    )

    fliplr: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Horizontal flip probability"
    )

    mosaic: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Mosaic augmentation probability"
    )

    # Hardware
    device: str = Field(
        default="0",
        description="Device(s) to use (0, 0,1, cpu)"
    )

    workers: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Number of dataloader workers"
    )

    # Early stopping and checkpointing
    patience: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Early stopping patience (epochs)"
    )

    save_period: int = Field(
        default=5,
        ge=-1,
        le=100,
        description="Save checkpoint every N epochs (-1 = disabled)"
    )

    # Validation
    val: bool = Field(
        default=True,
        description="Validate during training"
    )

    # Classes
    class_names: Optional[List[str]] = Field(
        default=None,
        description="Custom class names (auto-detected if None)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model": "yolo11n-seg.pt",
                "epochs": 50,
                "batch_size": 16,
                "imgsz": 640,
                "device": "0",
                "lr0": 0.01,
                "augment": True
            }
        }


class TrainingResult(BaseModel):
    """Result of YOLO training execution."""

    success: bool = Field(..., description="Whether training completed successfully")
    model_path: Optional[str] = Field(None, description="Path to trained model weights")
    best_model_path: Optional[str] = Field(None, description="Path to best model weights")

    # Training metrics
    final_metrics: Optional[Dict[str, float]] = Field(
        None,
        description="Final validation metrics"
    )

    # Training statistics
    epochs_completed: int = Field(0, description="Number of epochs completed")
    best_epoch: Optional[int] = Field(None, description="Epoch with best performance")
    training_time_seconds: float = Field(0.0, description="Total training time")

    # Model info
    model_size: Optional[YOLOModelSize] = Field(None, description="Model variant used")
    num_classes: int = Field(0, description="Number of classes trained")
    class_names: Optional[List[str]] = Field(None, description="Class names")

    # Paths
    output_dir: str = Field(..., description="Training output directory")

    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    training_log: Optional[str] = Field(None, description="Training log excerpt")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "model_path": "runs/segment/train/weights/last.pt",
                "best_model_path": "runs/segment/train/weights/best.pt",
                "final_metrics": {
                    "precision": 0.89,
                    "recall": 0.85,
                    "mAP50": 0.87,
                    "mAP50-95": 0.73
                },
                "epochs_completed": 50,
                "best_epoch": 42,
                "training_time_seconds": 3600.5,
                "model_size": "yolo11n-seg.pt",
                "num_classes": 7,
                "output_dir": "models/project_uuid/train_001"
            }
        }


class ModelExportConfig(BaseModel):
    """Configuration for model export."""

    format: ExportFormat = Field(
        ...,
        description="Export format"
    )

    imgsz: int = Field(
        default=640,
        ge=320,
        le=1280,
        description="Input image size for export"
    )

    optimize: bool = Field(
        default=True,
        description="Optimize for deployment"
    )

    half: bool = Field(
        default=False,
        description="Use FP16 precision (ONNX/TFLite)"
    )

    int8: bool = Field(
        default=False,
        description="Use INT8 quantization (TFLite)"
    )

    simplify: bool = Field(
        default=True,
        description="Simplify ONNX model"
    )

    batch: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Batch size for export"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "format": "tflite",
                "imgsz": 640,
                "optimize": True,
                "int8": True
            }
        }


class ModelMetadata(BaseModel):
    """Metadata for trained model."""

    model_id: str = Field(..., description="Unique model identifier")
    project_id: str = Field(..., description="Associated project ID")
    job_id: str = Field(..., description="Training job ID")

    # Model info
    model_size: YOLOModelSize = Field(..., description="Model variant")
    num_classes: int = Field(..., description="Number of classes")
    class_names: List[str] = Field(..., description="Class names")

    # Performance
    metrics: Dict[str, float] = Field(..., description="Validation metrics")

    # Training config
    training_config: Dict = Field(..., description="Training configuration used")

    # File paths
    weights_path: str = Field(..., description="Path to model weights")
    config_path: Optional[str] = Field(None, description="Path to model config")

    # Timestamps
    created_at: str = Field(..., description="Model creation timestamp")

    # Export status
    exported_formats: List[ExportFormat] = Field(
        default_factory=list,
        description="Available export formats"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "model_uuid",
                "project_id": "project_uuid",
                "job_id": "job_uuid",
                "model_size": "yolo11n-seg.pt",
                "num_classes": 7,
                "class_names": ["small_screw", "small_hole", "large_screw",
                               "large_hole", "bracket_A", "bracket_B", "surface"],
                "metrics": {
                    "mAP50": 0.87,
                    "mAP50-95": 0.73
                },
                "weights_path": "models/project_uuid/best.pt",
                "created_at": "2025-12-04T01:30:00Z",
                "exported_formats": ["onnx", "tflite"]
            }
        }
