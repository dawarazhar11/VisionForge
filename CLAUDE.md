# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VisionForge is an end-to-end pipeline: upload 3D assembly files → generate synthetic training images via Blender → train YOLO object detection models → deploy to iOS/Android. It targets detection of mechanical components (screws, holes, brackets) in 7 classes.

**Monorepo structure:**
- `backend/` — FastAPI + Celery API server
- `flutter_app/` — Primary cross-platform mobile app (use this, not the legacy `yolo_assembly_app/`)
- `blender/` — Blender Python scripts for synthetic data generation
- `training/` — YOLO training and export utilities
- `yolo-ios-app/` — Native Swift iOS app (separate from Flutter)
- `scripts/` — Docker/Podman lifecycle, setup, and E2E validation scripts
- `docs/` — Architecture, deployment, and workflow guides

## Git Flow & Linear

**GitHub:** https://github.com/dawarazhar11/VisionForge · **Linear:** VisionForge project (team: Dawar-personal)

```
master  ← production (GitHub default)
  ↑
develop ← integration branch
  ↑
feature/daw-XX-short-name
```

1. Start from `develop`: `git checkout develop && git pull origin develop`
2. Branch name must include the Linear ID: `feature/daw-37-wire-models-api`
3. Commit format: `type(scope): message (DAW-XX)` — e.g. `feat(flutter): wire ModelsScreen (DAW-37)`
4. Open PR **feature → develop**; at milestone completion, PR **develop → master**
5. Never commit directly to `master`. Never force-push `master`.

Linear hygiene: set the issue **In Progress** when starting; mark **Done** after the PR merges to `develop` and comment with the PR URL + merge commit SHA.

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

# Run tests (pytest.ini already adds -v, coverage, and asyncio auto mode)
pytest tests/

# Run a single test file
pytest tests/test_auth.py -v

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## E2E MVP Validation

```bash
# API pipeline: health → auth → upload → render → train → TFLite export (requires httpx)
python scripts/e2e/validate_mvp.py --smoke
python scripts/e2e/validate_mvp.py --full --upload-file "STEP Files/Test 1.STEP"
```

iOS camera inference is a manual step — see `docs/E2E_MVP_CHECKLIST.md`.

For dynamic-class validation, generate a non-desk test scene inside the worker
(`scripts/e2e/make_test_scene.py`; copy it into `backend/storage/e2e/` — the
storage volume is shared — then `podman exec yolo_celery_worker blender
--background --python /app/storage/e2e/make_test_scene.py` produces
`generic_parts.blend` with parts rotor/stator/bolt_m4/base_plate). Run the
pipeline against it — class names must flow from the auto class-map through
training to `/models/{id}/labels`.

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

# Generate synthetic dataset from the bundled desk scene
blender scene.blend --background --python blender/eevee_desk_scene17_dualpass.py

# Env-configurable wrapper (BLENDER_NUM_RENDERS, BLENDER_RESOLUTION_X/Y, ...)
BLENDER_NUM_RENDERS=200 blender scene.blend --background --python blender/eevee_api_wrapper.py

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
- `blender/` — Blender subprocess integration (`BlenderRunner`) and class-map resolution
- `config.py` — Pydantic Settings loaded from `.env`; cached via `@lru_cache()`
- `database.py` — SQLAlchemy async session setup

**Docker services:** `backend:8002`, `postgres:5433` (host) → 5432 (container), `redis:6379`, `celery_worker`, `celery_beat`, `portainer:9000` — all on `yolo_network`.

**Auth:** JWT (HS256), 15-min access tokens, 7-day refresh tokens, bcrypt passwords. Rate limiting: 60 req/min general, 5 req/min on auth endpoints.

**Async job flow:**
1. Client uploads file → stored in `backend/storage/uploads/`
2. API creates a `TrainingJob` record and enqueues a Celery task
3. Worker runs Blender render or YOLO training; updates job progress in PostgreSQL
4. Client polls `GET /api/v1/jobs/{id}` or streams SSE from `/jobs/{id}/stream`
5. Output artifacts saved to `backend/storage/datasets/` or `backend/storage/models/`

### Generic .blend rendering (DAW-119)

Any uploaded `.blend` file can be rendered via `blender/generic_blend_render_script.py`, driven by `VFORGE_*` env vars (`VFORGE_OUTPUT_DIR`, `VFORGE_NUM_RENDERS`, `VFORGE_RESOLUTION_X/Y`, `VFORGE_EEVEE_SAMPLES`, `VFORGE_CLASS_MAP_JSON`) set by `BlenderRunner.render_blend_geometry`.

The object→class mapping is resolved in `backend/app/blender/class_map.py` (`resolve_blend_class_map`) with this priority:
1. **metadata** — `class_map` in the project's `metadata_json` (set via `PATCH /projects/{id}` with a `class_map` body; read back via `GET /projects/{id}/class-map`)
2. **desk_preset** — auto-detected legacy desk scene (signature objects like `main_body`, `screw_01`)
3. **auto** — one class per unique mesh object name

**Class names flow end-to-end:** render stores `class_names` in the job's `metrics_json` → train task picks them up (priority: job config > render job > STEP PartFeatures, see `resolve_training_class_names` in `workers/tasks.py`) → `GET /models/{id}/class-names` (JSON) and `/labels` (txt) serve them → Flutter `YoloService` loads `labels.txt` downloaded next to the TFLite model.

**Containers:** the repo's `blender/` scripts are volume-mounted at `/app/blender_scripts` and located via `BLENDER_SCRIPTS_DIR` (see `find_blender_script` in `app/blender/runner.py`). Headless EEVEE requires the Mesa EGL/GLES libs baked into the Dockerfile. Training auto-falls back CUDA → MPS → CPU, and the trainer swaps `-seg`/plain YOLO weights to match the dataset's label format (render scripts emit detection boxes, not polygons).

### Flutter App (`flutter_app/lib/`)

- `providers/` — Riverpod state management
- `services/` — API client (`ApiService`) and YOLO inference engine (TFLite)
- `screens/` — Screen components (camera, projects, training dashboard, etc.)
- `models/` — Dart data classes
- TFLite models must be bundled in `flutter_app/assets/models/`

### Testing

- **Backend:** pytest with async support, SQLite in-memory (JSONB monkeypatched to JSON for test isolation), HTML coverage at `backend/htmlcov/`. Markers: `unit`, `integration`, `slow`.
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

7 classes, defined canonically in `backend/app/blender/class_map.py` (`DESK_CLASS_NAMES`):

`small_screw` (0), `small_hole` (1), `large_screw` (2), `large_hole` (3), `bracket_A` (4), `bracket_B` (5), `surface` (6)
