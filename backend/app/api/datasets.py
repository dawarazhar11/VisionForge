"""
Dataset management API endpoints - Download and preview generated datasets.
"""
import uuid
import zipfile
import io
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.training_job import TrainingJob

router = APIRouter()


@router.get("/{job_id}/preview")
def get_dataset_preview(
    job_id: uuid.UUID,
    image_index: int = Query(0, ge=0, description="Image index to preview"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Preview a rendered image from a dataset.

    Args:
        job_id: UUID of the rendering job
        image_index: Index of image to preview (0-based)
        db: Database session
        current_user: Authenticated user

    Returns:
        Image file (PNG)

    Raises:
        HTTPException: If job not found, unauthorized, or image not found
    """
    # Get job and verify ownership
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check ownership through project
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this dataset",
        )

    # Get output directory from result_data
    if not job.result_data or "output_dir" not in job.result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not generated yet",
        )

    output_dir = Path(job.result_data["output_dir"])

    if not output_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset directory not found",
        )

    # Find PNG images
    images = sorted(output_dir.glob("*.png"))

    if not images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No images found in dataset",
        )

    if image_index >= len(images):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image index {image_index} out of range (0-{len(images)-1})",
        )

    image_path = images[image_index]

    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=image_path.name,
    )


@router.get("/{job_id}/download")
def download_dataset(
    job_id: uuid.UUID,
    include_labels: bool = Query(True, description="Include YOLO label files"),
    include_images: bool = Query(True, description="Include rendered images"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download dataset as ZIP archive.

    Args:
        job_id: UUID of the rendering job
        include_labels: Whether to include .txt label files
        include_images: Whether to include .png image files
        db: Database session
        current_user: Authenticated user

    Returns:
        ZIP file stream

    Raises:
        HTTPException: If job not found, unauthorized, or dataset not available
    """
    # Get job and verify ownership
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check ownership through project
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this dataset",
        )

    # Get output directory from result_data
    if not job.result_data or "output_dir" not in job.result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not generated yet",
        )

    output_dir = Path(job.result_data["output_dir"])

    if not output_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset directory not found",
        )

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if include_images:
            for image_path in output_dir.glob("*.png"):
                zip_file.write(
                    image_path,
                    arcname=f"images/{image_path.name}"
                )

        if include_labels:
            for label_path in output_dir.glob("*.txt"):
                zip_file.write(
                    label_path,
                    arcname=f"labels/{label_path.name}"
                )

    zip_buffer.seek(0)

    # Generate filename
    project_name = job.project.name.replace(" ", "_")
    filename = f"{project_name}_dataset_{job_id}.zip"

    logger.info(f"Dataset downloaded: job_id={job_id}, user={current_user.email}")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{job_id}/info")
def get_dataset_info(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get dataset metadata and statistics.

    Args:
        job_id: UUID of the rendering job
        db: Database session
        current_user: Authenticated user

    Returns:
        Dataset metadata including file counts and size

    Raises:
        HTTPException: If job not found or unauthorized
    """
    # Get job and verify ownership
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check ownership through project
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this dataset",
        )

    # Get output directory from result_data
    if not job.result_data or "output_dir" not in job.result_data:
        return {
            "job_id": str(job_id),
            "status": job.status,
            "images_generated": 0,
            "labels_generated": 0,
            "dataset_ready": False,
        }

    output_dir = Path(job.result_data["output_dir"])

    if not output_dir.exists():
        return {
            "job_id": str(job_id),
            "status": job.status,
            "images_generated": 0,
            "labels_generated": 0,
            "dataset_ready": False,
        }

    # Calculate dataset statistics
    images = list(output_dir.glob("*.png"))
    labels = list(output_dir.glob("*.txt"))

    total_size = sum(f.stat().st_size for f in images + labels)

    return {
        "job_id": str(job_id),
        "project_id": str(job.project_id),
        "project_name": job.project.name,
        "status": job.status,
        "images_generated": len(images),
        "labels_generated": len(labels),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "output_dir": str(output_dir),
        "dataset_ready": len(images) > 0,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
