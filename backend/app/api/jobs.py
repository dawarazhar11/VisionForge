"""
Jobs API endpoints - Create and manage async training jobs.
"""
import uuid
import math
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from loguru import logger

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.assembly_project import AssemblyProject
from app.models.training_job import TrainingJob
from app.schemas.job import JobCreate, JobResponse, JobListResponse
from app.workers.tasks import echo_task, render_synthetic_data, train_yolo_model

router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new async job.

    Job types:
    - test: Simple echo task for testing
    - render: Generate synthetic data with Blender
    - train: Train YOLO model

    Args:
        job_data: Job creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        Created job data

    Raises:
        HTTPException: If project not found or invalid job type
    """
    # Verify project exists and user owns it
    project = (
        db.query(AssemblyProject)
        .filter(AssemblyProject.id == job_data.project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create jobs for this project",
        )

    # Create job in database
    job_id = uuid.uuid4()
    job = TrainingJob(
        id=job_id,
        project_id=job_data.project_id,
        stage=job_data.job_type,  # Store job_type in stage field
        status="PENDING",
        progress=0,
        config_json=job_data.config or {},
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch appropriate Celery task
    try:
        if job_data.job_type == "test":
            task = echo_task.delay(
                message=job_data.config.get("message", "Hello from Celery!") if job_data.config else "Hello!",
                job_id=str(job_id),
            )
        elif job_data.job_type == "render":
            task = render_synthetic_data.delay(
                project_id=str(job_data.project_id),
                job_id=str(job_id),
                config=job_data.config or {},
            )
        elif job_data.job_type == "train":
            task = train_yolo_model.delay(
                project_id=str(job_data.project_id),
                job_id=str(job_id),
                config=job_data.config or {},
            )
        else:
            db.delete(job)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid job type: {job_data.job_type}. Valid types: test, render, train",
            )

        # Store Celery task ID in metrics_json
        job.metrics_json = {"celery_task_id": task.id}
        db.commit()
        db.refresh(job)

        logger.info(
            f"Job {job_id} created: type={job_data.job_type}, celery_task={task.id}"
        )

    except Exception as e:
        logger.error(f"Failed to create Celery task: {e}")
        db.delete(job)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create background task",
        )

    return job


@router.get("/", response_model=JobListResponse)
def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all jobs for the current user with pagination.

    Args:
        page: Page number
        page_size: Items per page
        project_id: Optional project ID filter
        status: Optional status filter
        db: Database session
        current_user: Authenticated user

    Returns:
        Paginated list of jobs
    """
    # Build query - filter by user through project relationship
    query = (
        db.query(TrainingJob)
        .join(AssemblyProject)
        .filter(AssemblyProject.user_id == current_user.id)
    )

    if project_id:
        query = query.filter(TrainingJob.project_id == project_id)

    if status:
        query = query.filter(TrainingJob.status == status)

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

    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get job details by ID.

    Args:
        job_id: UUID of the job
        db: Database session
        current_user: Authenticated user

    Returns:
        Job details

    Raises:
        HTTPException: If job not found or unauthorized
    """
    job = (
        db.query(TrainingJob)
        .options(joinedload(TrainingJob.project))
        .filter(TrainingJob.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check ownership through project
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job",
        )

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Cancel a job (placeholder for now).

    Args:
        job_id: UUID of the job
        db: Database session
        current_user: Authenticated user

    Raises:
        HTTPException: If job not found or unauthorized
    """
    job = (
        db.query(TrainingJob)
        .options(joinedload(TrainingJob.project))
        .filter(TrainingJob.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check ownership through project
    if job.project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this job",
        )

    # TODO: Implement actual Celery task cancellation
    job.status = "CANCELLED"
    db.commit()

    logger.info(f"Job cancelled: {job_id}")
