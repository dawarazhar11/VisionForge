"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.config import settings
from app.database import init_db
from app.middleware import RateLimitMiddleware, AuthRateLimitMiddleware

# Configure loguru
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    description="""
## YOLO Assembly Vision API

Complete backend API for synthetic data generation, YOLO model training, and computer vision workflows.

### Features

* **User Authentication**: JWT-based authentication with access and refresh tokens
* **Project Management**: Upload and manage 3D assembly files (.blend, .obj, .stl, .fbx)
* **Async Job Queue**: Celery-powered background tasks for rendering and training
* **Real-time Progress**: Track job status and progress for long-running tasks

### Authentication Flow

1. **Register**: Create a new user account with email and password (`POST /api/v1/auth/register`)
2. **Login**: Get JWT access token and refresh token (`POST /api/v1/auth/login`)
3. **Access Protected Endpoints**: Include `Authorization: Bearer <access_token>` header in requests
4. **Refresh Token**: Get new access token when expired (`POST /api/v1/auth/refresh`)

### Quick Start

```python
# 1. Register a new user
POST /api/v1/auth/register
{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
}

# 2. Login to get tokens
POST /api/v1/auth/login
{
    "username": "user@example.com",
    "password": "securepassword123"
}
# Returns: {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}

# 3. Upload a project (with Authorization header)
POST /api/v1/projects/upload
Headers: Authorization: Bearer eyJ...
Form Data: file=@model.blend, name="My Project"

# 4. Create a rendering job
POST /api/v1/jobs/
Headers: Authorization: Bearer eyJ...
{
    "project_id": "uuid-here",
    "job_type": "render",
    "config": {"num_images": 100}
}
```

### Job Types

* **test**: Echo task for testing Celery integration
* **render**: Generate synthetic training data with Blender
* **train**: Train YOLO model on generated dataset
    """,
    contact={
        "name": "YOLO Assembly Vision Team",
        "email": "support@yolo-vision.example.com",
    },
    license_info={
        "name": "MIT License",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting (skip in test mode)
import os
if not os.getenv("TESTING"):
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        burst_size=10,
        exclude_paths=["/health", "/docs", "/redoc", "/openapi.json", "/api/v1/monitoring"]
    )

    app.add_middleware(
        AuthRateLimitMiddleware,
        login_attempts_per_minute=5,
        register_attempts_per_minute=3
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize database (skip in test mode - handled by fixtures)
    if not os.getenv("TESTING"):
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down API server")


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


# Import routers
from app.api import auth, projects, jobs, datasets, models, monitoring, webhooks

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["authentication"])
app.include_router(projects.router, prefix=f"{settings.API_PREFIX}/projects", tags=["projects"])
app.include_router(jobs.router, prefix=f"{settings.API_PREFIX}/jobs", tags=["jobs"])
app.include_router(datasets.router, prefix=f"{settings.API_PREFIX}/datasets", tags=["datasets"])
app.include_router(models.router, prefix=f"{settings.API_PREFIX}/models", tags=["models"])
app.include_router(monitoring.router, prefix=f"{settings.API_PREFIX}/monitoring", tags=["monitoring"])
app.include_router(webhooks.router, prefix=f"{settings.API_PREFIX}/webhooks", tags=["webhooks"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
