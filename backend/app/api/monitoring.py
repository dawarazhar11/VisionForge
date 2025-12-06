"""
Monitoring and health check endpoints for production observability.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import psutil
import torch
from datetime import datetime, timedelta
from typing import Dict, Any
from loguru import logger

from app.api.deps import get_db
from app.config import settings

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Basic health check endpoint.

    Returns:
        Status OK if service is running
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "YOLO Assembly Vision API",
        "version": "0.1.0"
    }


@router.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with dependency status.

    Checks:
    - Database connectivity
    - Redis connectivity
    - GPU availability
    - Disk space
    - Memory usage

    Returns:
        Detailed health status
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection OK"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        r = redis.from_url(str(settings.REDIS_URL), decode_responses=True)
        r.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection OK"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}"
        }
        logger.error(f"Redis health check failed: {e}")

    # Check GPU
    try:
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            health_status["checks"]["gpu"] = {
                "status": "healthy",
                "message": f"GPU available: {gpu_name}",
                "memory_gb": round(gpu_memory, 2)
            }
        else:
            health_status["checks"]["gpu"] = {
                "status": "degraded",
                "message": "GPU not available, using CPU"
            }
    except Exception as e:
        health_status["checks"]["gpu"] = {
            "status": "unknown",
            "message": f"GPU check error: {str(e)}"
        }

    # Check disk space
    try:
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)
        disk_percent = disk.percent

        if disk_percent > 90:
            health_status["status"] = "degraded"
            status_msg = "critical"
        elif disk_percent > 80:
            status_msg = "warning"
        else:
            status_msg = "healthy"

        health_status["checks"]["disk"] = {
            "status": status_msg,
            "free_gb": round(disk_free_gb, 2),
            "used_percent": disk_percent
        }
    except Exception as e:
        health_status["checks"]["disk"] = {
            "status": "unknown",
            "message": f"Disk check error: {str(e)}"
        }

    # Check memory
    try:
        memory = psutil.virtual_memory()
        memory_available_gb = memory.available / (1024**3)
        memory_percent = memory.percent

        if memory_percent > 90:
            health_status["status"] = "degraded"
            status_msg = "critical"
        elif memory_percent > 80:
            status_msg = "warning"
        else:
            status_msg = "healthy"

        health_status["checks"]["memory"] = {
            "status": status_msg,
            "available_gb": round(memory_available_gb, 2),
            "used_percent": memory_percent
        }
    except Exception as e:
        health_status["checks"]["memory"] = {
            "status": "unknown",
            "message": f"Memory check error: {str(e)}"
        }

    return health_status


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """
    Get system metrics for monitoring.

    Returns:
        System and application metrics
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "system": {},
        "application": {}
    }

    # System metrics
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics["system"]["cpu_percent"] = cpu_percent
        metrics["system"]["cpu_count"] = psutil.cpu_count()

        # Memory
        memory = psutil.virtual_memory()
        metrics["system"]["memory_total_gb"] = round(memory.total / (1024**3), 2)
        metrics["system"]["memory_used_gb"] = round(memory.used / (1024**3), 2)
        metrics["system"]["memory_percent"] = memory.percent

        # Disk
        disk = psutil.disk_usage('/')
        metrics["system"]["disk_total_gb"] = round(disk.total / (1024**3), 2)
        metrics["system"]["disk_used_gb"] = round(disk.used / (1024**3), 2)
        metrics["system"]["disk_percent"] = disk.percent

        # GPU
        if torch.cuda.is_available():
            metrics["system"]["gpu_available"] = True
            metrics["system"]["gpu_name"] = torch.cuda.get_device_name(0)
            # Note: Getting current GPU memory usage requires nvidia-ml-py3
            # metrics["system"]["gpu_memory_used_mb"] = ...
        else:
            metrics["system"]["gpu_available"] = False

    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        metrics["system"]["error"] = str(e)

    # Application metrics
    try:
        # Count total jobs by status
        from app.models.training_job import TrainingJob

        total_jobs = db.query(TrainingJob).count()
        pending_jobs = db.query(TrainingJob).filter(TrainingJob.status == "PENDING").count()
        running_jobs = db.query(TrainingJob).filter(TrainingJob.status == "RUNNING").count()
        success_jobs = db.query(TrainingJob).filter(TrainingJob.status == "SUCCESS").count()
        failed_jobs = db.query(TrainingJob).filter(TrainingJob.status == "FAILED").count()

        metrics["application"]["total_jobs"] = total_jobs
        metrics["application"]["pending_jobs"] = pending_jobs
        metrics["application"]["running_jobs"] = running_jobs
        metrics["application"]["success_jobs"] = success_jobs
        metrics["application"]["failed_jobs"] = failed_jobs

        # Count total users and projects
        from app.models.user import User
        from app.models.assembly_project import AssemblyProject

        total_users = db.query(User).count()
        total_projects = db.query(AssemblyProject).count()

        metrics["application"]["total_users"] = total_users
        metrics["application"]["total_projects"] = total_projects

        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_jobs = db.query(TrainingJob).filter(
            TrainingJob.created_at >= yesterday
        ).count()

        metrics["application"]["jobs_last_24h"] = recent_jobs

    except Exception as e:
        logger.error(f"Error collecting application metrics: {e}")
        metrics["application"]["error"] = str(e)

    return metrics


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe for Kubernetes/Docker.

    Checks if the service is ready to accept traffic.

    Returns:
        200 OK if ready, 503 if not ready
    """
    try:
        # Check database
        db.execute(text("SELECT 1"))

        # Check Redis
        r = redis.from_url(str(settings.REDIS_URL), decode_responses=True)
        r.ping()

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        from fastapi import Response
        return Response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/live")
def liveness_check():
    """
    Liveness probe for Kubernetes/Docker.

    Simple check if the process is alive.

    Returns:
        200 OK if alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
