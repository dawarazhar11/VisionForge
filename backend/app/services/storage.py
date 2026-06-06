"""
File storage service - Handle file uploads, validation, and storage.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID
import uuid
from fastapi import UploadFile, HTTPException, status
from loguru import logger

from app.config import get_settings


# Allowed file types for 3D models
ALLOWED_EXTENSIONS = {".blend", ".obj", ".stl", ".fbx", ".step", ".stp"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB in bytes

# STEP formats that go through the feature-recognition pipeline
STEP_EXTENSIONS = {".step", ".stp"}


class StorageService:
    """Service for managing file storage operations."""

    def __init__(self, base_upload_dir: str = "uploads"):
        """
        Initialize storage service.

        Args:
            base_upload_dir: Base directory for file uploads
        """
        self.base_upload_dir = Path(base_upload_dir)
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_file_type(self, filename: str) -> bool:
        """
        Validate file extension.

        Args:
            filename: Name of the file to validate

        Returns:
            True if file type is allowed, False otherwise
        """
        file_ext = Path(filename).suffix.lower()
        return file_ext in ALLOWED_EXTENSIONS

    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size.

        Args:
            file_size: Size of file in bytes

        Returns:
            True if file size is within limit, False otherwise
        """
        return file_size <= MAX_FILE_SIZE

    def get_file_extension(self, filename: str) -> str:
        """
        Get file extension from filename.

        Args:
            filename: Name of the file

        Returns:
            File extension (e.g., ".blend")
        """
        return Path(filename).suffix.lower()

    def generate_file_path(
        self, user_id: UUID, project_id: UUID, original_filename: str
    ) -> Path:
        """
        Generate unique file path for storage.

        Directory structure: uploads/{user_id}/{project_id}/filename.ext

        Args:
            user_id: UUID of the user
            project_id: UUID of the project
            original_filename: Original filename

        Returns:
            Path object for the file
        """
        # Get file extension
        file_ext = self.get_file_extension(original_filename)

        # Create directory structure
        user_dir = self.base_upload_dir / str(user_id)
        project_dir = user_dir / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename: original_name + extension
        # Keep original filename for better tracking
        filename = f"{Path(original_filename).stem}{file_ext}"
        file_path = project_dir / filename

        return file_path

    async def save_upload_file(
        self, upload_file: UploadFile, user_id: UUID, project_id: UUID
    ) -> Tuple[str, int]:
        """
        Save uploaded file to disk.

        Args:
            upload_file: FastAPI UploadFile object
            user_id: UUID of the user
            project_id: UUID of the project

        Returns:
            Tuple of (file_path, file_size)

        Raises:
            HTTPException: If file validation fails
        """
        # Validate file type
        if not self.validate_file_type(upload_file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Generate file path
        file_path = self.generate_file_path(user_id, project_id, upload_file.filename)

        try:
            # Save file in chunks to handle large files
            file_size = 0
            with file_path.open("wb") as f:
                while chunk := await upload_file.read(8192):  # Read 8KB chunks
                    file_size += len(chunk)

                    # Check file size during upload
                    if file_size > MAX_FILE_SIZE:
                        # Delete partially uploaded file
                        f.close()
                        file_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024*1024)}MB",
                        )

                    f.write(chunk)

            logger.info(
                f"File saved successfully: {file_path} (size: {file_size} bytes)"
            )
            return str(file_path), file_size

        except HTTPException:
            raise
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink(missing_ok=True)
            logger.error(f"Error saving file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file",
            )

    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            file_path: Path to the file

        Returns:
            True if file was deleted, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"File deleted: {file_path}")

                # Clean up empty directories
                # Remove project directory if empty
                project_dir = path.parent
                if project_dir.exists() and not any(project_dir.iterdir()):
                    project_dir.rmdir()
                    logger.info(f"Empty project directory removed: {project_dir}")

                    # Remove user directory if empty
                    user_dir = project_dir.parent
                    if user_dir.exists() and not any(user_dir.iterdir()):
                        user_dir.rmdir()
                        logger.info(f"Empty user directory removed: {user_dir}")

                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    def delete_project_directory(self, user_id: UUID, project_id: UUID) -> bool:
        """
        Delete entire project directory.

        Args:
            user_id: UUID of the user
            project_id: UUID of the project

        Returns:
            True if directory was deleted, False otherwise
        """
        try:
            project_dir = self.base_upload_dir / str(user_id) / str(project_id)
            if project_dir.exists():
                shutil.rmtree(project_dir)
                logger.info(f"Project directory deleted: {project_dir}")

                # Clean up empty user directory
                user_dir = project_dir.parent
                if user_dir.exists() and not any(user_dir.iterdir()):
                    user_dir.rmdir()
                    logger.info(f"Empty user directory removed: {user_dir}")

                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting project directory: {e}")
            return False

    def get_user_storage_used(self, user_id: UUID) -> int:
        """
        Calculate total storage used by a user.

        Args:
            user_id: UUID of the user

        Returns:
            Total storage used in bytes
        """
        user_dir = self.base_upload_dir / str(user_id)
        if not user_dir.exists():
            return 0

        total_size = 0
        for file_path in user_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size

        return total_size

    def check_storage_quota(self, user_id: UUID, quota_mb: int) -> bool:
        """
        Check if user has exceeded storage quota.

        Args:
            user_id: UUID of the user
            quota_mb: Storage quota in megabytes

        Returns:
            True if within quota, False if exceeded
        """
        used_bytes = self.get_user_storage_used(user_id)
        quota_bytes = quota_mb * 1024 * 1024
        return used_bytes < quota_bytes


# Global storage service instance — use settings.UPLOAD_DIR so files land in the mounted volume
storage_service = StorageService(base_upload_dir=get_settings().UPLOAD_DIR)
