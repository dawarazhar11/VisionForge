"""
Celery tasks for async job processing.
"""
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from celery import Task
from loguru import logger
from sqlalchemy.orm import Session
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.training_job import TrainingJob
from app.models.assembly_project import AssemblyProject
from app.models.part_feature import PartFeature, FEATURE_CLASS_ORDER
from app.models.user import User
from app.blender.runner import BlenderRunner
from app.blender.config import BlenderRenderConfig, get_blender_path
from app.services.webhooks import webhook_service
from app.services.storage import STEP_EXTENSIONS
from app.services.step_parser import STEPParser
from app.config import get_settings


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


def get_user_webhook_urls(db: Session, project_id: str) -> List[str]:
    """
    Get webhook URLs for a project's user.

    Args:
        db: Database session
        project_id: UUID of the project

    Returns:
        List of webhook URLs
    """
    project = db.query(AssemblyProject).filter(
        AssemblyProject.id == project_id
    ).first()

    if not project:
        return []

    user = db.query(User).filter(User.id == project.user_id).first()
    if not user or not user.webhook_urls:
        return []

    return user.webhook_urls if isinstance(user.webhook_urls, list) else []


def send_webhook_notification(
    db: Session,
    job_id: str,
    job_type: str,
    status: str,
    result_data: Dict[str, Any] = None,
    error_message: str = None
):
    """
    Send webhook notification for job completion.

    Args:
        db: Database session
        job_id: UUID of the job
        job_type: Type of job (render, train, etc.)
        status: Job status (SUCCESS, FAILED)
        result_data: Optional result data
        error_message: Optional error message
    """
    try:
        # Get job to find project
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            return

        # Get webhook URLs from user
        webhook_urls = get_user_webhook_urls(db, str(job.project_id))

        if not webhook_urls:
            logger.debug(f"No webhook URLs configured for job {job_id}")
            return

        # Send webhook notifications asynchronously
        asyncio.run(
            webhook_service.notify_job_completed(
                webhook_urls=webhook_urls,
                job_id=str(job_id),
                job_type=job_type,
                status=status,
                result_data=result_data,
                error_message=error_message
            )
        )

        logger.info(f"Webhook notifications sent for job {job_id} to {len(webhook_urls)} URLs")

    except Exception as e:
        # Don't fail the task if webhook fails
        logger.error(f"Error sending webhook notification for job {job_id}: {e}")


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
                merged = dict(job.metrics_json)  # Create a copy
                merged.update(result_data)
                job.metrics_json = merged  # Assign new dict to trigger SQLAlchemy change detection
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
        update_job_status(self.db, job_id, "RUNNING", progress=0)

        project = self.db.query(AssemblyProject).filter(
            AssemblyProject.id == project_id
        ).first()
        if not project:
            error_msg = f"Project {project_id} not found"
            update_job_status(self.db, job_id, "FAILED", result_data={"error": error_msg})
            return {"status": "failed", "error": error_msg}

        if not os.path.exists(project.file_path):
            error_msg = f"Project file not found: {project.file_path}"
            update_job_status(self.db, job_id, "FAILED", result_data={"error": error_msg})
            return {"status": "failed", "error": error_msg}

        try:
            render_config = BlenderRenderConfig(**config)
        except Exception as e:
            error_msg = f"Invalid render configuration: {e}"
            update_job_status(self.db, job_id, "FAILED", result_data={"error": error_msg})
            return {"status": "failed", "error": error_msg}

        output_dir = (
            Path(get_settings().DATASET_DIR) / str(project_id) / f"render_{job_id}"
        ).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            blender_path = get_blender_path()
        except FileNotFoundError as e:
            error_msg = f"Blender not found: {e}"
            update_job_status(self.db, job_id, "FAILED", result_data={"error": error_msg})
            return {"status": "failed", "error": error_msg}

        # ── Branch on file type ───────────────────────────────────────────────
        file_ext = Path(project.file_path).suffix.lower()
        is_step  = file_ext in STEP_EXTENSIONS

        if is_step:
            render_result, extra = _run_step_pipeline(
                db=self.db,
                project_id=project_id,
                job_id=job_id,
                file_path=project.file_path,
                output_dir=output_dir,
                render_config=render_config,
                blender_path=blender_path,
            )
        else:
            extra = {}

            def _progress(p: int):
                update_job_status(self.db, job_id, "RUNNING", progress=p)

            runner = BlenderRunner(blender_path=blender_path, progress_callback=_progress)
            render_result = runner.render_synthetic_data(
                blend_file_path=project.file_path,
                output_dir=str(output_dir),
                config=render_config,
                project_id=UUID(project_id),
                job_id=UUID(job_id),
            )

        # ── Handle result ─────────────────────────────────────────────────────
        if render_result.success:
            result = {
                "project_id":      project_id,
                "output_dir":      render_result.output_dir,
                "images_generated": render_result.images_generated,
                "labels_generated": render_result.labels_generated,
                "status":          "completed",
                **extra,
            }
            update_job_status(self.db, job_id, "SUCCESS", progress=100, result_data=result)
            logger.info(f"Rendering completed: {result}")
            send_webhook_notification(
                db=self.db, job_id=job_id, job_type="render",
                status="SUCCESS", result_data=result,
            )
            return result
        else:
            error_msg = render_result.error_message
            logger.error(f"Rendering failed: {error_msg}")
            update_job_status(
                self.db, job_id, "FAILED", progress=0,
                result_data={
                    "error":       error_msg,
                    "blender_log": (render_result.blender_log or "")[-500:],
                },
            )
            send_webhook_notification(
                db=self.db, job_id=job_id, job_type="render",
                status="FAILED", error_message=error_msg,
            )
            return {"status": "failed", "error": error_msg,
                    "images_generated": render_result.images_generated}

    except Exception as e:
        error_msg = f"Unexpected error during rendering: {e}"
        logger.exception(error_msg)
        update_job_status(self.db, job_id, "FAILED", progress=0,
                         result_data={"error": error_msg})
        return {"status": "failed", "error": error_msg}


def _run_step_pipeline(
    db: Session,
    project_id: str,
    job_id: str,
    file_path: str,
    output_dir: Path,
    render_config: BlenderRenderConfig,
    blender_path: str,
) -> tuple:
    """
    STEP rendering sub-pipeline (module-level so Celery serialisation is clean):
      1. Parse STEP → features + STL
      2. Persist PartFeature records to DB
      3. Render with generic step_render_script.py

    Returns (BlenderExecutionResult, extra_result_dict).
    """
    from app.blender.config import BlenderExecutionResult as BER

    # ── Phase 1: feature recognition (5%) ───────────────────────────────
    update_job_status(db, job_id, "RUNNING", progress=5)

    parse_dir = output_dir / "step_parse"
    parse_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Parsing STEP: {file_path}")
    parse_result = STEPParser().parse(file_path, str(parse_dir))

    if not parse_result.success:
        return BER(
            success=False, output_dir=str(output_dir),
            images_generated=0, labels_generated=0,
            error_message=f"STEP parse failed: {parse_result.error}",
        ), {}

    update_job_status(db, job_id, "RUNNING", progress=15)

    # ── Phase 2: persist features to DB (15→30%) ────────────────────────
    db.query(PartFeature).filter(
        PartFeature.project_id == UUID(project_id)
    ).delete()

    for feat in parse_result.features:
        db.add(PartFeature(
            project_id=UUID(project_id),
            feature_type=feat.feature_type,
            class_index=feat.class_index,
            center_x=feat.center_x,
            center_y=feat.center_y,
            center_z=feat.center_z,
            normal_x=feat.normal_x,
            normal_y=feat.normal_y,
            normal_z=feat.normal_z,
            radius=feat.radius,
            depth=feat.depth,
            properties_json=feat.properties,
        ))
    db.commit()
    logger.info(
        f"Saved {len(parse_result.features)} features "
        f"({parse_result.stats.get('by_type', {})})"
    )

    # Write features.json for the Blender script
    features_json = parse_dir / "features.json"
    features_json.write_text(json.dumps({
        "features":    [f.to_dict() for f in parse_result.features],
        "class_names": parse_result.class_names,
    }, indent=2))

    update_job_status(db, job_id, "RUNNING", progress=30)

    # ── Phase 3: render (30→100%) ────────────────────────────────────────
    def _progress(p: int):
        update_job_status(db, job_id, "RUNNING", progress=30 + int(p * 0.70))

    runner = BlenderRunner(blender_path=blender_path, progress_callback=_progress)
    render_result = runner.render_step_geometry(
        stl_path=parse_result.stl_path,
        features_json_path=str(features_json),
        output_dir=str(output_dir),
        config=render_config,
    )

    extra = {
        "features_recognised": len(parse_result.features),
        "feature_types":       parse_result.stats.get("by_type", {}),
        "class_names":         parse_result.class_names,
        "stl_path":            parse_result.stl_path,
    }
    return render_result, extra


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

        # Derive class names from PartFeature records for this project
        features = (
            self.db.query(PartFeature)
            .filter(PartFeature.project_id == project_id)
            .all()
        )
        if features:
            present_indices = sorted({f.class_index for f in features})
            dynamic_class_names = [
                FEATURE_CLASS_ORDER[i] for i in present_indices if i < len(FEATURE_CLASS_ORDER)
            ]
            config = {**config, "class_names": dynamic_class_names}
            logger.info(f"Using dynamic class names from part features: {dynamic_class_names}")
        else:
            logger.warning(f"No PartFeature records for project {project_id}; using config class_names")

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
        output_base = Path(get_settings().MODEL_DIR)
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
