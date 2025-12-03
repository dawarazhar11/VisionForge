"""
Celery tasks for async job processing.
"""
import time
from typing import Dict, Any
from celery import Task
from loguru import logger
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.training_job import TrainingJob


class DatabaseTask(Task):
    """Base task with database session support."""

    _db: Session = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        """Close database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


def update_job_status(
    db: Session, job_id: str, status: str, progress: int = None, result_data: Dict[str, Any] = None
):
    """
    Update job status in database.

    Args:
        db: Database session
        job_id: UUID of the job
        status: New status (PENDING, RUNNING, SUCCESS, FAILED)
        progress: Progress percentage (0-100)
        result_data: Optional result data to store
    """
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if job:
        job.status = status
        if progress is not None:
            job.progress = progress
        if result_data:
            # Merge result_data into metrics_json (preserving celery_task_id)
            if job.metrics_json:
                job.metrics_json.update(result_data)
            else:
                job.metrics_json = result_data
        db.commit()
        logger.info(f"Job {job_id} status updated: {status} (progress: {progress}%)")


@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.echo_task")
def echo_task(self, message: str, job_id: str = None) -> Dict[str, Any]:
    """
    Simple echo task for testing Celery.

    Args:
        message: Message to echo back
        job_id: Optional job ID to update status

    Returns:
        Dict with echoed message and task info
    """
    logger.info(f"Echo task started: {message}")

    # Update job status if job_id provided
    if job_id:
        update_job_status(self.db, job_id, "RUNNING", progress=0)

    # Simulate work with progress updates
    for i in range(1, 6):
        time.sleep(1)
        progress = i * 20
        logger.info(f"Echo task progress: {progress}%")

        if job_id:
            update_job_status(self.db, job_id, "RUNNING", progress=progress)

    result = {
        "message": f"Echo: {message}",
        "task_id": self.request.id,
        "timestamp": time.time(),
    }

    # Mark job as complete
    if job_id:
        update_job_status(self.db, job_id, "SUCCESS", progress=100, result_data=result)

    logger.info(f"Echo task completed: {result}")
    return result


@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.render_synthetic_data")
def render_synthetic_data(
    self, project_id: str, job_id: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Render synthetic data using Blender (placeholder for now).

    Args:
        project_id: UUID of the assembly project
        job_id: UUID of the training job
        config: Rendering configuration

    Returns:
        Dict with rendering results
    """
    logger.info(f"Rendering task started for project {project_id}")

    # Update job status
    update_job_status(self.db, job_id, "RUNNING", progress=0)

    # TODO: Implement actual Blender rendering in Week 5-8
    # For now, just simulate the work
    logger.info(f"Rendering config: {config}")

    for i in range(1, 11):
        time.sleep(0.5)
        progress = i * 10
        logger.info(f"Rendering progress: {progress}%")
        update_job_status(self.db, job_id, "RUNNING", progress=progress)

    result = {
        "project_id": project_id,
        "images_generated": config.get("num_images", 100),
        "dataset_path": f"outputs/{project_id}/dataset.zip",
        "status": "completed",
    }

    update_job_status(self.db, job_id, "SUCCESS", progress=100, result_data=result)

    logger.info(f"Rendering completed: {result}")
    return result


@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.train_yolo_model")
def train_yolo_model(
    self, project_id: str, job_id: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Train YOLO model (placeholder for now).

    Args:
        project_id: UUID of the assembly project
        job_id: UUID of the training job
        config: Training configuration

    Returns:
        Dict with training results
    """
    logger.info(f"Training task started for project {project_id}")

    # Update job status
    update_job_status(self.db, job_id, "RUNNING", progress=0)

    # TODO: Implement actual YOLO training in Week 9-12
    # For now, just simulate the work
    logger.info(f"Training config: {config}")

    for i in range(1, 11):
        time.sleep(1)
        progress = i * 10
        logger.info(f"Training progress: {progress}%")
        update_job_status(self.db, job_id, "RUNNING", progress=progress)

    result = {
        "project_id": project_id,
        "model_path": f"models/{project_id}/best.pt",
        "accuracy": 0.95,
        "epochs_trained": config.get("epochs", 50),
        "status": "completed",
    }

    update_job_status(self.db, job_id, "SUCCESS", progress=100, result_data=result)

    logger.info(f"Training completed: {result}")
    return result
