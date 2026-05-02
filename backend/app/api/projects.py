"""
Projects API endpoints - File upload and project management.
"""
import uuid
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger
import math

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.assembly_project import AssemblyProject
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.services.storage import storage_service

router = APIRouter()


@router.post("/upload", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def upload_project(
    file: UploadFile = File(..., description="3D model file (.step, .stp, .blend, .obj, .stl, .fbx)"),
    name: str = Form(..., description="Project name"),
    description: Optional[str] = Form(None, description="Project description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a new assembly project file.

    Args:
        file: 3D model file (Blender, OBJ, STL, FBX)
        name: Project name
        description: Optional project description
        db: Database session
        current_user: Authenticated user

    Returns:
        Created project data

    Raises:
        HTTPException: If file validation fails or storage quota exceeded
    """
    # Check storage quota
    if not storage_service.check_storage_quota(
        current_user.id, current_user.storage_quota_mb
    ):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Storage quota exceeded. Current quota: {current_user.storage_quota_mb}MB",
        )

    # Generate project ID
    project_id = uuid.uuid4()

    try:
        # Save file to storage
        file_path, file_size = await storage_service.save_upload_file(
            file, current_user.id, project_id
        )

        # Get file type
        file_type = storage_service.get_file_extension(file.filename)

        # Convert file size from bytes to MB
        file_size_mb = file_size / (1024 * 1024)

        # Create project in database
        project = AssemblyProject(
            id=project_id,
            user_id=current_user.id,
            name=name,
            description=description,
            file_path=file_path,
            file_size_mb=file_size_mb,
            file_type=file_type,
            status="uploaded",
        )

        db.add(project)
        db.commit()
        db.refresh(project)

        logger.info(
            f"Project created: {project.id} by user {current_user.email} (size: {file_size} bytes)"
        )

        return project

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        # Clean up file if database operation fails
        storage_service.delete_project_directory(current_user.id, project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project",
        )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new project with JSON data (for testing/existing blend files).

    Args:
        project_data: Project creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        Created project data
    """
    project_id = uuid.uuid4()

    project = AssemblyProject(
        id=project_id,
        user_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
        file_path=f"placeholder/{project_id}.blend",  # Placeholder for JSON-created projects
        file_size_mb=0.0,  # No file uploaded yet
        file_type="blend",  # Default type
        status="created",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    logger.info(f"Project created: {project.id} - {project.name}")
    return project


@router.get("/", response_model=ProjectListResponse)
def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all projects for the current user with pagination.

    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page (max 100)
        db: Database session
        current_user: Authenticated user

    Returns:
        Paginated list of projects
    """
    # Get total count
    total = db.query(func.count(AssemblyProject.id)).filter(
        AssemblyProject.user_id == current_user.id
    ).scalar()

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    # Get projects for current page
    projects = (
        db.query(AssemblyProject)
        .filter(AssemblyProject.user_id == current_user.id)
        .order_by(AssemblyProject.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ProjectListResponse(
        projects=projects,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get project details by ID.

    Args:
        project_id: UUID of the project
        db: Database session
        current_user: Authenticated user

    Returns:
        Project details

    Raises:
        HTTPException: If project not found or unauthorized
    """
    project = db.query(AssemblyProject).filter(AssemblyProject.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project",
        )

    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update project metadata (name, description).

    Args:
        project_id: UUID of the project
        project_update: Updated project data
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated project details

    Raises:
        HTTPException: If project not found or unauthorized
    """
    project = db.query(AssemblyProject).filter(AssemblyProject.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project",
        )

    # Update fields if provided
    if project_update.name is not None:
        project.name = project_update.name
    if project_update.description is not None:
        project.description = project_update.description

    db.commit()
    db.refresh(project)

    logger.info(f"Project updated: {project.id}")

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a project and its associated file.

    Args:
        project_id: UUID of the project
        db: Database session
        current_user: Authenticated user

    Raises:
        HTTPException: If project not found or unauthorized
    """
    project = db.query(AssemblyProject).filter(AssemblyProject.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project",
        )

    # Delete file from storage
    storage_service.delete_project_directory(current_user.id, project.id)

    # Delete from database
    db.delete(project)
    db.commit()

    logger.info(f"Project deleted: {project_id}")


@router.get("/{project_id}/file")
def download_project_file(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download the project file.

    Args:
        project_id: UUID of the project
        db: Database session
        current_user: Authenticated user

    Returns:
        File response with the project file

    Raises:
        HTTPException: If project not found, unauthorized, or file missing
    """
    project = db.query(AssemblyProject).filter(AssemblyProject.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project",
        )

    # Check if file exists
    from pathlib import Path

    file_path = Path(project.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project file not found on server",
        )

    # Return file
    return FileResponse(
        path=str(file_path),
        filename=f"{project.name}{project.file_type}",
        media_type="application/octet-stream",
    )
