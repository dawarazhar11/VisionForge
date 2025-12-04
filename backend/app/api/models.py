"""
Models API endpoints - Manage trained YOLO models.
"""
import uuid
import math
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.assembly_project import AssemblyProject
from app.models.training_job import TrainingJob
from app.schemas.model import (
    ModelResponse,
    ModelListResponse,
    ModelExportRequest,
    ModelExportResponse,
)
from app.training.runner import YOLOTrainer

router = APIRouter()


def _create_model_response(job: TrainingJob) -> ModelResponse:
    """
    Create ModelResponse from TrainingJob.

    Args:
        job: Training job with completed training

    Returns:
        ModelResponse object
    """
    result_data = job.result_data or {}

    return ModelResponse(
        id=job.id,
        project_id=job.project_id,
        model_path=result_data.get("model_path", ""),
        best_model_path=result_data.get("best_model_path"),
        model_size=result_data.get("model_size", "unknown"),
        num_classes=result_data.get("num_classes", 0),
        class_names=result_data.get("class_names"),
        metrics=result_data.get("metrics"),
        epochs_completed=result_data.get("epochs_completed", 0),
        best_epoch=result_data.get("best_epoch"),
        training_time_seconds=result_data.get("training_time_seconds", 0.0),
        created_at=job.created_at,
        status=job.status,
    )


@router.get("/", response_model=ModelListResponse)
def list_models(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all trained models for the current user.

    Args:
        page: Page number
        page_size: Items per page
        project_id: Optional project ID filter
        db: Database session
        current_user: Authenticated user

    Returns:
        Paginated list of trained models
    """
    # Build query - filter training jobs with type="train" and status="SUCCESS"
    query = (
        db.query(TrainingJob)
        .join(AssemblyProject)
        .filter(
            AssemblyProject.user_id == current_user.id,
            TrainingJob.stage == "train",
            TrainingJob.status == "SUCCESS",
        )
    )

    if project_id:
        query = query.filter(TrainingJob.project_id == project_id)

    # Get total count
    total = query.count()

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    # Get jobs for current page
    jobs = (
        query.order_by(TrainingJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Convert to ModelResponse
    models = [_create_model_response(job) for job in jobs]

    return ModelListResponse(
        models=models,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get trained model details by ID.

    Args:
        model_id: UUID of the training job (model ID)
        db: Database session
        current_user: Authenticated user

    Returns:
        Model details

    Raises:
        HTTPException: If model not found or unauthorized
    """
    job = (
        db.query(TrainingJob)
        .filter(
            TrainingJob.id == model_id,
            TrainingJob.stage == "train",
            TrainingJob.status == "SUCCESS",
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check ownership through project
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model",
        )

    return _create_model_response(job)


@router.get("/{model_id}/download")
def download_model(
    model_id: uuid.UUID,
    weights_type: str = Query("best", regex="^(best|last)$", description="Weights to download (best or last)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download trained model weights.

    Args:
        model_id: UUID of the training job (model ID)
        weights_type: Type of weights to download ('best' or 'last')
        db: Database session
        current_user: Authenticated user

    Returns:
        Model weights file (.pt)

    Raises:
        HTTPException: If model not found, unauthorized, or weights don't exist
    """
    job = (
        db.query(TrainingJob)
        .filter(
            TrainingJob.id == model_id,
            TrainingJob.stage == "train",
            TrainingJob.status == "SUCCESS",
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check ownership
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model",
        )

    # Get weights path
    result_data = job.result_data or {}
    if weights_type == "best":
        weights_path = result_data.get("best_model_path")
    else:
        weights_path = result_data.get("model_path")

    if not weights_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{weights_type.capitalize()} weights not found for this model",
        )

    # Verify file exists
    weights_file = Path(weights_path)
    if not weights_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model weights file not found on disk",
        )

    # Return file
    filename = f"model_{model_id}_{weights_type}.pt"
    return FileResponse(
        path=str(weights_file),
        media_type="application/octet-stream",
        filename=filename,
    )


@router.post("/{model_id}/export", response_model=ModelExportResponse)
def export_model(
    model_id: uuid.UUID,
    export_request: ModelExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Export trained model to different format (ONNX, TFLite, CoreML, etc.).

    Args:
        model_id: UUID of the training job (model ID)
        export_request: Export configuration
        db: Database session
        current_user: Authenticated user

    Returns:
        Export result with path to exported model

    Raises:
        HTTPException: If model not found, unauthorized, or export fails
    """
    job = (
        db.query(TrainingJob)
        .filter(
            TrainingJob.id == model_id,
            TrainingJob.stage == "train",
            TrainingJob.status == "SUCCESS",
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check ownership
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model",
        )

    # Get best model path
    result_data = job.result_data or {}
    best_model_path = result_data.get("best_model_path")

    if not best_model_path or not Path(best_model_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model weights not found",
        )

    logger.info(f"Exporting model {model_id} to {export_request.format}")

    try:
        # Create temporary trainer for export functionality
        trainer = YOLOTrainer(
            config=None,  # Not needed for export
            output_dir=Path(result_data.get("output_dir", "models")),
        )

        # Build export arguments
        export_kwargs = {
            "imgsz": export_request.imgsz,
            "optimize": export_request.optimize,
            "half": export_request.half,
            "int8": export_request.int8,
            "simplify": export_request.simplify,
            "batch": export_request.batch,
        }

        # Execute export
        export_path = trainer.export_model(
            model_path=Path(best_model_path),
            format=export_request.format,
            **export_kwargs,
        )

        # Get file size
        file_size_mb = export_path.stat().st_size / (1024 * 1024)

        logger.info(f"Model exported successfully to {export_path}")

        return ModelExportResponse(
            success=True,
            export_path=str(export_path),
            format=export_request.format,
            file_size_mb=round(file_size_mb, 2),
            error_message=None,
        )

    except Exception as e:
        error_msg = f"Export failed: {str(e)}"
        logger.error(error_msg)

        return ModelExportResponse(
            success=False,
            export_path=None,
            format=export_request.format,
            file_size_mb=None,
            error_message=error_msg,
        )


@router.get("/{model_id}/export/{format}/download")
def download_exported_model(
    model_id: uuid.UUID,
    format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download previously exported model.

    Args:
        model_id: UUID of the training job (model ID)
        format: Export format (onnx, tflite, coreml, etc.)
        db: Database session
        current_user: Authenticated user

    Returns:
        Exported model file

    Raises:
        HTTPException: If model or exported file not found
    """
    job = (
        db.query(TrainingJob)
        .filter(
            TrainingJob.id == model_id,
            TrainingJob.stage == "train",
            TrainingJob.status == "SUCCESS",
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check ownership
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model",
        )

    # Get output directory
    result_data = job.result_data or {}
    output_dir = Path(result_data.get("output_dir", "models"))

    # Find exported model file
    # Look in runs directory for exported model
    runs_dir = output_dir / "runs"
    if runs_dir.exists():
        # Search for exported model with this format
        exported_files = list(runs_dir.rglob(f"*.{format}"))
        if not exported_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No exported {format} model found. Please export first.",
            )

        # Use the most recent export
        exported_file = max(exported_files, key=lambda p: p.stat().st_mtime)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exported models directory not found",
        )

    # Return file
    filename = f"model_{model_id}.{format}"
    media_type = {
        "onnx": "application/octet-stream",
        "tflite": "application/octet-stream",
        "torchscript": "application/octet-stream",
        "coreml": "application/zip",  # CoreML is packaged
    }.get(format, "application/octet-stream")

    return FileResponse(
        path=str(exported_file),
        media_type=media_type,
        filename=filename,
    )
