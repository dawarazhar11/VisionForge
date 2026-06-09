#!/bin/sh
set -e

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found — installing Python dependencies..."
  pip install --retries 10 --timeout 120 -r /tmp/requirements-core.txt
  pip install cadquery 2>/dev/null || echo "cadquery unavailable for this arch — STEP feature recognition disabled"
fi

exec "$@"
