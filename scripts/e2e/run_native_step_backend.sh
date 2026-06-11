#!/bin/bash
# Native backend + worker for STEP testing on macOS (DAW-73 / DAW-118).
#
# ARM64 containers can't run cadquery (STEP feature/part extraction), so for
# live STEP sessions the API + worker run natively while postgres/redis stay
# in Podman. Stops the containerized backend/worker first to free port 8002.
#
# Usage:  ./scripts/e2e/run_native_step_backend.sh
# Stop:   Ctrl-C (kills both processes)

set -euo pipefail
cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"
PY="$REPO_ROOT/backend/.venv-test/bin/python"

echo "Stopping containerized backend + worker (postgres/redis stay up)..."
podman stop yolo_backend yolo_celery_worker yolo_celery_beat 2>/dev/null || true

export DATABASE_URL="postgresql://yolo_user:yolo_dev_pass@localhost:5433/yolo_assembly"
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
export SECRET_KEY="dev-secret-key-change-in-production"
export UPLOAD_DIR="$REPO_ROOT/backend/storage/uploads"
export DATASET_DIR="$REPO_ROOT/backend/storage/datasets"
export MODEL_DIR="$REPO_ROOT/backend/storage/models"
export BLENDER_SCRIPTS_DIR="$REPO_ROOT/blender"
export CORS_ORIGINS='["*"]'

command -v blender >/dev/null || export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"

echo "Starting native Celery worker (cadquery + Blender available)..."
(cd backend && "$PY" -m celery -A app.celery_app.celery_app worker \
    --loglevel=info -Q rendering,training,default,celery) &
WORKER_PID=$!

echo "Starting native FastAPI on 0.0.0.0:8002 ..."
(cd backend && "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8002) &
API_PID=$!

trap 'kill $WORKER_PID $API_PID 2>/dev/null' EXIT
echo ""
echo "Native stack up. Phone backend URL: http://$(ipconfig getifaddr en0):8002"
wait
