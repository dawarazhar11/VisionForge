#!/usr/bin/env bash
#
# One-shot native backend setup + verification (macOS / Linux).
#
# Creates a Python venv, installs the FULL dependency set (API, workers,
# YOLO training, and the complete TFLite export toolchain), attempts the
# optional STEP parser (cadquery), then verifies every critical import so
# you know in one run whether the machine is ready — no dependency
# whack-a-mole.
#
# Usage:   scripts/setup/setup_backend.sh [venv_dir]
# Default venv: backend/.venv
#
# Windows: use Docker instead — `docker compose up -d --build` installs the
# same requirements.txt into the image (x86_64 also gets cadquery/STEP).
set -uo pipefail

cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"
VENV="${1:-$REPO_ROOT/backend/.venv}"
PY_BIN="${PYTHON:-python3.11}"

echo "============================================================"
echo "VisionForge backend setup"
echo "  repo:   $REPO_ROOT"
echo "  venv:   $VENV"
echo "  python: $PY_BIN"
echo "============================================================"

command -v "$PY_BIN" >/dev/null 2>&1 || {
  echo "ERROR: $PY_BIN not found. Install Python 3.11 (e.g. brew install python@3.11"
  echo "       or apt install python3.11 python3.11-venv) and re-run."
  exit 1
}

# 1. venv (idempotent)
if [ ! -x "$VENV/bin/python" ]; then
  echo "→ creating venv"
  "$PY_BIN" -m venv "$VENV"
fi
PIP="$VENV/bin/python -m pip"

# 2. dependencies
echo "→ upgrading pip"
$PIP install --upgrade pip >/dev/null
echo "→ installing requirements (this pulls TensorFlow + the export chain; takes a few minutes)"
# cadquery has no ARM64-Linux wheels; install core first, then attempt it
# separately so the run never hard-fails on that one optional package.
grep -v '^cadquery' backend/requirements.txt > /tmp/vf-core-reqs.txt
$PIP install -r /tmp/vf-core-reqs.txt
echo "→ attempting cadquery (STEP parsing — optional, skipped if no wheel for this arch)"
$PIP install cadquery>=2.4.0 || echo "  ! cadquery unavailable here — STEP feature/part recognition will be disabled"

# 3. verification — import every critical package, report PASS/FAIL
echo "→ verifying imports"
"$VENV/bin/python" - <<'PY'
import importlib, sys
checks = [
    ("fastapi", "API framework"),
    ("uvicorn", "ASGI server"),
    ("celery", "task queue"),
    ("sqlalchemy", "ORM"),
    ("torch", "PyTorch"),
    ("ultralytics", "YOLO"),
    ("tensorflow", "TFLite export"),
    ("tf_keras", "TFLite export (legacy keras)"),
    ("onnx", "ONNX"),
    ("onnx2tf", "ONNX→TF"),
    ("onnx_graphsurgeon", "ONNX graph surgeon"),
    ("ai_edge_litert", "TFLite runtime"),
]
optional = [("cadquery", "STEP parsing (optional)")]
ok, bad = [], []
for mod, desc in checks:
    try:
        importlib.import_module(mod); ok.append(mod)
    except Exception as e:
        bad.append((mod, desc, str(e)[:60]))
print("\n--- verification ---")
for m in ok: print(f"  PASS  {m}")
for mod, desc, _ in bad: print(f"  FAIL  {mod}  ({desc})")
for mod, desc in optional:
    try:
        importlib.import_module(mod); print(f"  PASS  {mod}  ({desc})")
    except Exception:
        print(f"  SKIP  {mod}  ({desc} — not available on this arch)")
if bad:
    print(f"\n❌ {len(bad)} critical package(s) missing — see errors above.")
    sys.exit(1)
print("\n✅ All critical dependencies present. Backend is ready.")
PY
STATUS=$?

echo "============================================================"
if [ $STATUS -eq 0 ]; then
  echo "Setup complete. Activate with:  source $VENV/bin/activate"
else
  echo "Setup finished WITH ERRORS — fix the FAIL lines above and re-run."
fi
echo "============================================================"
exit $STATUS
