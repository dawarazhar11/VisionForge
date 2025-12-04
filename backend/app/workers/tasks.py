"""
Celery tasks for async job processing.
"""
import os
import time
from pathlib import Path
from typing import Dict, Any
from celery import Task
from loguru import logger
from sqlalchemy.orm import Session
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.training_job import TrainingJob
from app.models.assembly_project import AssemblyProject
from app.blender.runner import BlenderRunner
from app.blender.config import BlenderRenderConfig, get_blender_path


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
    Render synthetic data using Blender.

    Args:
        project_id: UUID of the assembly project
        job_id: UUID of the training job
        config: Rendering configuration

    Returns:
        Dict with rendering results
    """
    logger.info(f"Rendering task started for project {project_id}")

    try:
        # Update job status
        update_job_status(self.db, job_id, "RUNNING", progress=0)

        # Get project from database
        project = self.db.query(AssemblyProject).filter(
            AssemblyProject.id == project_id
        ).first()

        if not project:
            error_msg = f"Project {project_id} not found"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        # Ensure project file exists
        if not os.path.exists(project.file_path):
            error_msg = f"Project file not found: {project.file_path}"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        # Validate render configuration
        try:
            render_config = BlenderRenderConfig(**config)
        except Exception as e:
            error_msg = f"Invalid render configuration: {str(e)}"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        # Create output directory
        output_base = Path("datasets")
        output_dir = output_base / str(project_id) / f"render_{job_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Rendering config: {render_config}")
        logger.info(f"Output directory: {output_dir}")

        # Progress callback for real-time updates
        def progress_callback(progress: int):
            """Update job progress in database."""
            update_job_status(self.db, job_id, "RUNNING", progress=progress)
            logger.info(f"Rendering progress: {progress}%")

        # Initialize Blender runner with auto-detected path
        try:
            blender_path = get_blender_path()
        except FileNotFoundError as e:
            error_msg = f"Blender not found: {str(e)}"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        runner = BlenderRunner(
            blender_path=blender_path,
            progress_callback=progress_callback
        )

        # Execute rendering
        logger.info(f"Starting Blender render: {project.file_path}")
        render_result = runner.render_synthetic_data(
            blend_file_path=project.file_path,
            output_dir=str(output_dir),
            config=render_config,
            project_id=UUID(project_id),
            job_id=UUID(job_id)
        )

        # Handle rendering result
        if render_result.success:
            result = {
                "project_id": project_id,
                "output_dir": render_result.output_dir,
                "images_generated": render_result.images_generated,
                "labels_generated": render_result.labels_generated,
                "status": "completed",
            }

            update_job_status(self.db, job_id, "SUCCESS", progress=100, result_data=result)
            logger.info(f"Rendering completed successfully: {result}")
            return result
        else:
            error_msg = render_result.error_message
            logger.error(f"Rendering failed: {error_msg}")

            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={
                    "error": error_msg,
                    "blender_log": render_result.blender_log[-500:] if render_result.blender_log else None
                }
            )
            return {
                "status": "failed",
                "error": error_msg,
                "images_generated": render_result.images_generated
            }

    except Exception as e:
        error_msg = f"Unexpected error during rendering: {str(e)}"
        logger.exception(error_msg)

        update_job_status(
            self.db, job_id, "FAILED", progress=0,
            result_data={"error": error_msg}
        )
        return {"status": "failed", "error": error_msg}


@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.train_yolo_model")
def train_yolo_model(
    self, project_id: str, job_id: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Train YOLO model on synthetic dataset.

    Args:
        project_id: UUID of the assembly project
        job_id: UUID of the training job
        config: Training configuration

    Returns:
        Dict with training results
    """
    logger.info(f"Training task started for project {project_id}")

    try:
        # Update job status
        update_job_status(self.db, job_id, "RUNNING", progress=0)

        # Get job from database to find dataset
        job = self.db.query(TrainingJob).filter(
            TrainingJob.id == job_id
        ).first()

        if not job:
            error_msg = f"Job {job_id} not found"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        # Find the rendering job to get dataset location
        # Look for the most recent successful render job for this project
        render_job = (
            self.db.query(TrainingJob)
            .filter(
                TrainingJob.project_id == project_id,
                TrainingJob.stage == "render",
                TrainingJob.status == "SUCCESS"
            )
            .order_by(TrainingJob.created_at.desc())
            .first()
        )

        if not render_job or not render_job.metrics_json:
            error_msg = "No successful rendering found for this project. Please render dataset first."
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        # Get dataset directory from render job (stored in metrics_json)
        dataset_dir = Path(render_job.metrics_json.get("output_dir"))
        if not dataset_dir.exists():
            error_msg = f"Dataset directory not found: {dataset_dir}"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        logger.info(f"Found dataset at: {dataset_dir}")

        # Validate training configuration
        try:
            from app.training.config import YOLOTrainingConfig
            training_config = YOLOTrainingConfig(**config)
        except Exception as e:
            error_msg = f"Invalid training configuration: {str(e)}"
            logger.error(error_msg)
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}

        # Create output directory for trained models
        output_base = Path("models")
        output_dir = output_base / str(project_id) / f"train_{job_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Training config: {training_config}")
        logger.info(f"Output directory: {output_dir}")

        # Progress callback for real-time updates
        def progress_callback(progress: int, message: str):
            """Update job progress in database."""
            update_job_status(self.db, job_id, "RUNNING", progress=progress)
            logger.info(f"Training: {message} ({progress}%)")

        # Initialize YOLO trainer
        from app.training.runner import YOLOTrainer
        trainer = YOLOTrainer(
            config=training_config,
            output_dir=output_dir,
            progress_callback=progress_callback
        )

        # Execute training
        logger.info(f"Starting YOLO training on dataset: {dataset_dir}")
        training_result = trainer.train(
            dataset_dir=dataset_dir,
            project_name=f"project_{project_id}"
        )

        # Handle training result
        if training_result.success:
            result = {
                "project_id": project_id,
                "model_path": training_result.model_path,
                "best_model_path": training_result.best_model_path,
                "output_dir": training_result.output_dir,
                "epochs_completed": training_result.epochs_completed,
                "best_epoch": training_result.best_epoch,
                "training_time_seconds": training_result.training_time_seconds,
                "model_size": training_result.model_size.value,
                "num_classes": training_result.num_classes,
                "class_names": training_result.class_names,
                "metrics": training_result.final_metrics,
                "status": "completed",
            }

            update_job_status(self.db, job_id, "SUCCESS", progress=100, result_data=result)
            logger.info(f"Training completed successfully: {result}")
            return result
        else:
            error_msg = training_result.error_message or "Training failed"
            logger.error(f"Training failed: {error_msg}")

            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={
                    "error": error_msg,
                    "training_log": training_result.training_log,
                    "epochs_completed": training_result.epochs_completed,
                }
            )
            return {
                "status": "failed",
                "error": error_msg,
                "epochs_completed": training_result.epochs_completed
            }

    except Exception as e:
        error_msg = f"Unexpected error during training: {str(e)}"
        logger.exception(error_msg)

        update_job_status(
            self.db, job_id, "FAILED", progress=0,
            result_data={"error": error_msg}
        )
        return {"status": "failed", "error": error_msg}
