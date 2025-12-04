"""
Dataset preparation utilities for YOLO training.
"""
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml
from loguru import logger
import random


class YOLODatasetPreparer:
    """Prepare rendered synthetic data for YOLO training."""

    def __init__(self, output_base_dir: Path):
        """
        Initialize dataset preparer.

        Args:
            output_base_dir: Base directory for organized dataset
        """
        self.output_base_dir = Path(output_base_dir)
        self.train_dir = self.output_base_dir / "train"
        self.val_dir = self.output_base_dir / "val"

    def prepare_dataset(
        self,
        source_dir: Path,
        train_split: float = 0.8,
        class_names: Optional[List[str]] = None,
    ) -> Tuple[Path, Dict[str, int]]:
        """
        Organize rendered images and labels into YOLO training structure.

        Expected source directory structure:
        source_dir/
            ├── render_0000.png
            ├── render_0000.txt  (YOLO format labels)
            ├── render_0001.png
            ├── render_0001.txt
            └── ...

        Output structure:
        output_base_dir/
            ├── train/
            │   ├── images/
            │   │   ├── img_0001.png
            │   │   └── ...
            │   └── labels/
            │       ├── img_0001.txt
            │       └── ...
            ├── val/
            │   ├── images/
            │   └── labels/
            └── data.yaml

        Args:
            source_dir: Directory containing rendered images and labels
            train_split: Fraction of data for training (0.0-1.0)
            class_names: List of class names (auto-detected if None)

        Returns:
            Tuple of (data.yaml path, dataset statistics dict)
        """
        source_dir = Path(source_dir)

        # Validate source directory
        if not source_dir.exists():
            raise ValueError(f"Source directory not found: {source_dir}")

        # Find all image files
        image_files = sorted(source_dir.glob("*.png"))
        if not image_files:
            raise ValueError(f"No PNG images found in {source_dir}")

        logger.info(f"Found {len(image_files)} images in {source_dir}")

        # Verify corresponding labels exist
        label_files = []
        for img_path in image_files:
            label_path = img_path.with_suffix(".txt")
            if label_path.exists():
                label_files.append(label_path)
            else:
                logger.warning(f"Missing label for {img_path.name}")

        if len(label_files) == 0:
            raise ValueError("No label files found")

        logger.info(f"Found {len(label_files)} matching labels")

        # Auto-detect class names if not provided
        if class_names is None:
            class_names = self._detect_class_names(label_files)
            logger.info(f"Auto-detected {len(class_names)} classes: {class_names}")

        # Create directory structure
        self._create_directory_structure()

        # Split dataset
        dataset_pairs = list(zip(image_files[:len(label_files)], label_files))
        random.shuffle(dataset_pairs)

        split_idx = int(len(dataset_pairs) * train_split)
        train_pairs = dataset_pairs[:split_idx]
        val_pairs = dataset_pairs[split_idx:]

        logger.info(f"Split: {len(train_pairs)} train, {len(val_pairs)} val")

        # Copy files to train/val directories
        self._copy_dataset_files(train_pairs, self.train_dir)
        self._copy_dataset_files(val_pairs, self.val_dir)

        # Create data.yaml
        data_yaml_path = self._create_data_yaml(class_names)

        # Generate statistics
        stats = {
            "total_images": len(image_files),
            "total_labels": len(label_files),
            "train_images": len(train_pairs),
            "val_images": len(val_pairs),
            "num_classes": len(class_names),
        }

        logger.info(f"Dataset prepared successfully at {self.output_base_dir}")
        return data_yaml_path, stats

    def _create_directory_structure(self):
        """Create train/val directory structure."""
        for split_dir in [self.train_dir, self.val_dir]:
            (split_dir / "images").mkdir(parents=True, exist_ok=True)
            (split_dir / "labels").mkdir(parents=True, exist_ok=True)

        logger.debug(f"Created directory structure at {self.output_base_dir}")

    def _copy_dataset_files(
        self,
        dataset_pairs: List[Tuple[Path, Path]],
        target_dir: Path
    ):
        """
        Copy image/label pairs to target directory.

        Args:
            dataset_pairs: List of (image_path, label_path) tuples
            target_dir: Target directory (train or val)
        """
        images_dir = target_dir / "images"
        labels_dir = target_dir / "labels"

        for img_path, label_path in dataset_pairs:
            # Copy image
            shutil.copy2(img_path, images_dir / img_path.name)

            # Copy label
            shutil.copy2(label_path, labels_dir / label_path.name)

    def _detect_class_names(self, label_files: List[Path]) -> List[str]:
        """
        Auto-detect class names by scanning label files.

        Assumes YOLO format: class_id x_center y_center width height

        Args:
            label_files: List of label file paths

        Returns:
            List of detected class names
        """
        class_ids = set()

        for label_path in label_files:
            try:
                with open(label_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_id = int(parts[0])
                            class_ids.add(class_id)
            except Exception as e:
                logger.warning(f"Failed to parse {label_path}: {e}")

        # Generate generic class names
        max_class_id = max(class_ids) if class_ids else 0
        class_names = [f"class_{i}" for i in range(max_class_id + 1)]

        return class_names

    def _create_data_yaml(self, class_names: List[str]) -> Path:
        """
        Create YOLO data.yaml configuration file.

        Args:
            class_names: List of class names

        Returns:
            Path to created data.yaml
        """
        data_yaml = {
            "path": str(self.output_base_dir.absolute()),
            "train": "train/images",
            "val": "val/images",
            "names": {i: name for i, name in enumerate(class_names)},
            "nc": len(class_names),
        }

        yaml_path = self.output_base_dir / "data.yaml"

        with open(yaml_path, "w") as f:
            yaml.dump(data_yaml, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Created data.yaml at {yaml_path}")
        return yaml_path

    def cleanup(self):
        """Remove prepared dataset directory."""
        if self.output_base_dir.exists():
            shutil.rmtree(self.output_base_dir)
            logger.info(f"Cleaned up dataset directory: {self.output_base_dir}")
