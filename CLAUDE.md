# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VisionForge is an end-to-end pipeline: upload 3D assembly files → generate synthetic training images via Blender → train YOLO object detection models → deploy to iOS/Android. It targets detection of mechanical components (screws, holes, brackets) in 7 classes.

**Monorepo structure:**
- `backend/` — FastAPI + Celery API server
- `flutter_app/` — Primary cross-platform mobile app (use this, not `yolo_assembly_app/`)
- `blender/` — Blender Python scripts for synthetic data generation
- `training/` — YOLO training and export utilities
- `yolo-ios-app/` — Native Swift iOS app (separate from Flutter)
- `scripts/` — Docker/Podman lifecycle and setup scripts
- `docs/` — Architecture, deployment, and workflow guides

## Backend Commands

```bash
# Full stack (preferred for dev)
docker compose up -d
# API docs at http://localhost:8002/docs

# Local dev without Docker
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Run tests
pytest tests/ -v --cov=app --cov-report=html

# Run a single test file
pytest tests/test_auth.py -v

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Flutter App Commands

```bash
cd flutter_app
flutter pub get
flutter run                      # Debug on connected device
flutter run --release            # Release mode
flutter build apk --release      # Android APK
flutter build ios                # iOS (requires macOS + Xcode)
flutter analyze                  # Lint
flutter test                     # Unit tests
```

## Training & Blender

```bash
# Validate training environment
python training/setup_training_env.py

# Generate synthetic dataset via Blender
blender scene.blend --background --python blender/eevee_desk_scene17_dualpass.py

# Train and export YOLO model (CoreML + TFLite)
python training/train_yolo_model.py
```

## Architecture

### Backend (`backend/app/`)

FastAPI app with these layers:
- `api/` — Route handlers grouped by resource (auth, projects, jobs, datasets, models, monitoring)
- `models/` — SQLAlchemy ORM: `User`, `AssemblyProject`, `TrainingJob`, `Model`
- `schemas/` — Pydantic request/response validation
- `services/` — Business logic (auth.py, storage.py, webhooks.py)
- `workers/` — Celery tasks for async rendering and training jobs
- `config.py` — Pydantic Settings loaded from `.env`; cached via `@lru_cache()`
- `database.py` — SQLAlchemy async session setup

**Docker services:** `backend:8002`, `postgres:5433`, `redis:6379`, `celery_worker`, `celery_beat`, `portainer:9000` — all on `yolo_network`.

**Auth:** JWT (HS256), 15-min access tokens, 7-day refresh tokens, bcrypt passwords. Rate limiting: 60 req/min general, 5 req/min on auth endpoints.

**Async job flow:**
1. Client uploads file → stored in `backend/storage/uploads/`
2. API creates a `TrainingJob` record and enqueues a Celery task
3. Worker runs Blender render or YOLO training; updates job progress in PostgreSQL
4. Client polls `GET /api/v1/jobs/{id}` or streams SSE from `/jobs/{id}/stream`
5. Output artifacts saved to `backend/storage/datasets/` or `backend/storage/models/`

### Flutter App (`flutter_app/lib/`)

- `providers/` — Riverpod state management
- `services/` — API client (`ApiService`) and YOLO inference engine (TFLite)
- `screens/` — 17 screens (camera, projects, training dashboard, etc.)
- `models/` — Dart data classes
- TFLite models must be bundled in `flutter_app/assets/models/`

### Testing

- **Backend:** pytest with async support, SQLite in-memory (JSONB monkeypatched to JSON for test isolation), HTML coverage at `backend/htmlcov/`
- **Flutter:** `flutter test` for unit/widget tests

## Key Config Variables

Set these in `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<change in production>
ACCESS_TOKEN_EXPIRE_MINUTES=15
UPLOAD_DIR, DATASET_DIR, MODEL_DIR
CORS_ORIGINS
```

## Platform Notes

### Mac (ARM64) — current dev environment

Run the stack with Podman (not Docker Desktop) via `podman-compose up -d`. Key differences from x86_64:

- **cadquery unavailable**: `cadquery-ocp` has no ARM64 Linux wheels, so STEP feature recognition is skipped in containers. The worker returns a clear `"cadquery is not installed"` error and marks the job FAILED — this is expected. To test the STEP cadquery path locally, use the macOS venv outside Docker: `pip install cadquery` works on macOS ARM64.
- **Blender 4.3.2 (apt)**: ARM64 containers get Blender via apt (Debian trixie, 4.3.2) instead of the 4.4.0 binary. Functionally equivalent for our scripts.
- **alembic migrations in Docker**: `env.py` reads `DATABASE_URL` env var to override the `localhost:5433` in `alembic.ini`. Never edit `alembic.ini` directly for Docker use.

### Windows (x86_64) — future production

When deploying on Windows x86_64 Docker:

1. Install Docker Desktop for Windows or Podman Desktop.
2. `docker compose up -d` — everything uses the x86_64 paths automatically.
3. cadquery-ocp **does** have x86_64 Linux wheels, so STEP feature recognition will work end-to-end.
4. Blender 4.4.0 official binary is used (x86_64 branch in Dockerfile).
5. No changes to application code needed — the Dockerfile architecture detection handles it.

```bash
# Windows PowerShell or CMD
docker compose up -d
# Then run migrations if first boot:
docker compose exec backend alembic upgrade head
```

### Celery queue routing

`celery_app.py` routes tasks to named queues: `render_synthetic_data` → `rendering`, `train_yolo_model` → `training`. The `docker-compose.yml` celery_worker command must include `-Q rendering,training,default,celery` or tasks will stay PENDING forever.

## Detection Classes

`small_screw`, `small_hole`, `large_screw_left`, `large_screw_right`, `large_hole`, `bracket_A`, `bracket_B`, `surface`
