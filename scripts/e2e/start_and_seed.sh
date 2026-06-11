#!/bin/bash
# Start native STEP-capable backend + seed a known login account.
# For local dev/testing only (DAW-73). Creds are env-overridable.
set -uo pipefail
cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"
PY="$REPO_ROOT/backend/.venv-test/bin/python"

ADMIN_EMAIL="${ADMIN_EMAIL:-admin@visionforge.local}"
ADMIN_PASS="${ADMIN_PASS:-Admin!2345}"

echo "Freeing port 8002 (stopping containerized backend/worker)..."
podman stop yolo_backend yolo_celery_worker yolo_celery_beat >/dev/null 2>&1 || true

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

echo "Starting native Celery worker + FastAPI..."
# --pool=solo: PyTorch MPS (Apple GPU) aborts (SIGABRT) if initialised in a
# forked child, which Celery's default prefork pool does. solo runs tasks in
# the main process so MPS training works on macOS. (Containers use prefork +
# CPU/CUDA, which are fork-safe.)
( cd backend && "$PY" -m celery -A app.celery_app.celery_app worker \
    --loglevel=warning --pool=solo -Q rendering,training,default,celery ) &
WORKER_PID=$!
( cd backend && "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8002 \
    --log-level warning ) &
API_PID=$!
trap 'kill $WORKER_PID $API_PID 2>/dev/null' EXIT

echo "Waiting for API health..."
until curl -s -m 2 http://localhost:8002/health | grep -q healthy; do sleep 2; done

echo "Seeding account $ADMIN_EMAIL ..."
curl -s -X POST http://localhost:8002/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\",\"full_name\":\"Admin\"}" \
  -o /tmp/seed_result.json -w "register HTTP %{http_code}\n" || true

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || echo '<mac-ip>')"
echo "============================================================"
echo "READY. Phone backend URL:  http://$LAN_IP:8002"
echo "Login:  $ADMIN_EMAIL  /  $ADMIN_PASS"
echo "============================================================"
wait
