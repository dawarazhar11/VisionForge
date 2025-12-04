"""
YOLO model training runner with Ultralytics integration.
"""
import time
from pathlib import Path
from typing import Dict, Optional, Callable
import yaml
from loguru import logger

from app.training.config import (
    YOLOTrainingConfig,
    TrainingResult,
    YOLOModelSize,
)
from app.training.dataset import YOLODatasetPreparer


class YOLOTrainer:
    """
    YOLO model training orchestrator.

    Handles dataset preparation, model initialization, training execution,
    and result tracking for YOLO segmentation models.
    """

    def __init__(
        self,
        config: YOLOTrainingConfig,
        output_dir: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        """
        Initialize YOLO trainer.

        Args:
            config: Training configuration
            output_dir: Directory for training outputs
            progress_callback: Optional callback for progress updates
                              Signature: callback(progress: int, message: str)
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback

        self.model = None
        self.data_yaml_path: Optional[Path] = None
        self.dataset_stats: Optional[Dict] = None

    def train(
        self,
        dataset_dir: Path,
        project_name: str = "yolo_training",
    ) -> TrainingResult:
        """
        Execute complete training pipeline.

        Steps:
        1. Prepare dataset in YOLO format
        2. Initialize YOLO model
        3. Execute training
        4. Save results and metadata

        Args:
            dataset_dir: Directory containing rendered images and labels
            project_name: Project name for organizing training runs

        Returns:
            TrainingResult with metrics and paths
        """
        start_time = time.time()

        try:
            # Step 1: Prepare dataset
            self._update_progress(10, "Preparing dataset...")
            self._prepare_dataset(dataset_dir)

            # Step 2: Initialize model
            self._update_progress(20, "Loading YOLO model...")
            self._initialize_model()

            # Step 3: Train model
            self._update_progress(30, "Training model...")
            training_results = self._execute_training(project_name)

            # Step 4: Extract results
            self._update_progress(95, "Saving results...")
            result = self._create_training_result(
                training_results,
                start_time,
                success=True
            )

            self._update_progress(100, "Training completed!")
            logger.info(f"Training completed successfully in {result.training_time_seconds:.1f}s")

            return result

        except Exception as e:
            logger.error(f"Training failed: {e}")

            # Create failure result
            result = TrainingResult(
                success=False,
                model_path=None,
                best_model_path=None,
                final_metrics=None,
                epochs_completed=0,
                best_epoch=None,
                training_time_seconds=time.time() - start_time,
                model_size=self.config.model,
                num_classes=0,
                class_names=self.config.class_names,
                output_dir=str(self.output_dir),
                error_message=str(e),
                training_log=None,
            )

            self._update_progress(100, f"Training failed: {str(e)}")
            return result

    def _prepare_dataset(self, dataset_dir: Path):
        """
        Prepare dataset for YOLO training.

        Args:
            dataset_dir: Source directory with rendered images/labels
        """
        logger.info(f"Preparing dataset from {dataset_dir}")

        preparer = YOLODatasetPreparer(
            output_base_dir=self.output_dir / "dataset"
        )

        self.data_yaml_path, self.dataset_stats = preparer.prepare_dataset(
            source_dir=dataset_dir,
            train_split=0.8,
            class_names=self.config.class_names,
        )

        logger.info(f"Dataset prepared: {self.dataset_stats}")

    def _initialize_model(self):
        """Initialize YOLO model with specified configuration."""
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError(
                "Ultralytics not installed. Install with: pip install ultralytics"
            )

        logger.info(f"Initializing YOLO model: {self.config.model.value}")

        # Load pretrained or scratch model
        if self.config.pretrained:
            model_path = self.config.model.value  # e.g., "yolo11n-seg.pt"
            logger.info(f"Loading pretrained weights: {model_path}")
        else:
            # For training from scratch, use .yaml config instead of .pt
            model_path = self.config.model.value.replace(".pt", ".yaml")
            logger.info(f"Training from scratch with config: {model_path}")

        self.model = YOLO(model_path)

    def _execute_training(self, project_name: str) -> Dict:
        """
        Execute YOLO training with Ultralytics.

        Args:
            project_name: Project name for organizing runs

        Returns:
            Training results dictionary from Ultralytics
        """
        logger.info("Starting YOLO training...")

        # Build training arguments
        train_args = {
            "data": str(self.data_yaml_path),
            "epochs": self.config.epochs,
            "batch": self.config.batch_size,
            "imgsz": self.config.imgsz,
            "device": self.config.device,
            "workers": self.config.workers,
            "optimizer": self.config.optimizer,
            "lr0": self.config.lr0,
            "lrf": self.config.lrf,
            "momentum": self.config.momentum,
            "weight_decay": self.config.weight_decay,
            "patience": self.config.patience,
            "save_period": self.config.save_period,
            "project": str(self.output_dir / "runs"),
            "name": project_name,
            "exist_ok": True,
            "val": self.config.val,
        }

        # Add augmentation parameters if enabled
        if self.config.augment:
            train_args.update({
                "hsv_h": self.config.hsv_h,
                "hsv_s": self.config.hsv_s,
                "hsv_v": self.config.hsv_v,
                "degrees": self.config.degrees,
                "translate": self.config.translate,
                "scale": self.config.scale,
                "flipud": self.config.flipud,
                "fliplr": self.config.fliplr,
                "mosaic": self.config.mosaic,
            })

        logger.debug(f"Training arguments: {train_args}")

        # Execute training
        results = self.model.train(**train_args)

        logger.info("Training completed")
        return results

    def _create_training_result(
        self,
        training_results,
        start_time: float,
        success: bool,
    ) -> TrainingResult:
        """
        Create TrainingResult from Ultralytics training results.

        Args:
            training_results: Results object from model.train()
            start_time: Training start timestamp
            success: Whether training succeeded

        Returns:
            TrainingResult object
        """
        training_time = time.time() - start_time

        if not success:
            return TrainingResult(
                success=False,
                model_path=None,
                best_model_path=None,
                final_metrics=None,
                epochs_completed=0,
                best_epoch=None,
                training_time_seconds=training_time,
                model_size=self.config.model,
                num_classes=self.dataset_stats.get("num_classes", 0) if self.dataset_stats else 0,
                class_names=self.config.class_names,
                output_dir=str(self.output_dir),
                error_message="Training failed",
                training_log=None,
            )

        # Extract paths from training results
        save_dir = Path(training_results.save_dir)
        weights_dir = save_dir / "weights"

        last_weights = weights_dir / "last.pt"
        best_weights = weights_dir / "best.pt"

        # Extract final metrics
        try:
            final_metrics = {
                "precision": float(training_results.results_dict.get("metrics/precision(B)", 0)),
                "recall": float(training_results.results_dict.get("metrics/recall(B)", 0)),
                "mAP50": float(training_results.results_dict.get("metrics/mAP50(B)", 0)),
                "mAP50-95": float(training_results.results_dict.get("metrics/mAP50-95(B)", 0)),
            }
        except Exception as e:
            logger.warning(f"Failed to extract metrics: {e}")
            final_metrics = {}

        # Get number of epochs completed
        epochs_completed = self.config.epochs  # Ultralytics completes all epochs unless early stopped

        # Find best epoch (if available)
        best_epoch = None
        try:
            # Try to extract from results
            best_epoch = training_results.best_epoch
        except AttributeError:
            logger.debug("Best epoch not available in results")

        return TrainingResult(
            success=True,
            model_path=str(last_weights) if last_weights.exists() else None,
            best_model_path=str(best_weights) if best_weights.exists() else None,
            final_metrics=final_metrics,
            epochs_completed=epochs_completed,
            best_epoch=best_epoch,
            training_time_seconds=training_time,
            model_size=self.config.model,
            num_classes=self.dataset_stats.get("num_classes", 0) if self.dataset_stats else 0,
            class_names=self.config.class_names or [],
            output_dir=str(self.output_dir),
            error_message=None,
            training_log=None,
        )

    def _update_progress(self, progress: int, message: str):
        """
        Update progress via callback if provided.

        Args:
            progress: Progress percentage (0-100)
            message: Status message
        """
        logger.debug(f"Progress: {progress}% - {message}")

        if self.progress_callback:
            try:
                self.progress_callback(progress, message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def export_model(
        self,
        model_path: Path,
        format: str = "onnx",
        **export_kwargs
    ) -> Path:
        """
        Export trained model to different formats.

        Args:
            model_path: Path to trained .pt model
            format: Export format (onnx, tflite, coreml, etc.)
            **export_kwargs: Additional export arguments

        Returns:
            Path to exported model
        """
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError("Ultralytics not installed")

        logger.info(f"Exporting model to {format} format...")

        model = YOLO(str(model_path))
        export_path = model.export(format=format, **export_kwargs)

        logger.info(f"Model exported to {export_path}")
        return Path(export_path)
