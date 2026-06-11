# VisionForge Backend Setup

The backend needs: API/worker deps, YOLO training (PyTorch + Ultralytics),
and the **full TFLite export toolchain** (TensorFlow + ONNX chain). All of it
is pinned in `backend/requirements.txt` — nothing is installed at runtime —
so any environment gets a complete install in one shot.

## Windows / Linux x86_64 — Docker (recommended)

x86_64 is the easiest target: `cadquery` has wheels, so **STEP parsing works
inside the container** — the whole stack runs in Docker, no native steps.

```bash
docker compose up -d --build      # builds image from requirements.txt
docker compose exec backend alembic upgrade head   # first boot only
# API: http://localhost:8002/docs
```

Verify everything imported correctly:

```bash
docker compose exec backend python -c "import tensorflow, tf_keras, onnx, onnx2tf, onnx_graphsurgeon, ai_edge_litert, cadquery, ultralytics; print('OK: all deps present')"
```

That single line confirms the export toolchain **and** cadquery are in the
image. If it prints `OK`, render → train → TFLite export → STEP all work.

## Native (macOS, or Linux without Docker)

Use the one-shot script — creates a venv, installs the full set, attempts
cadquery, and verifies every critical import with a PASS/FAIL report:

```bash
scripts/setup/setup_backend.sh            # venv at backend/.venv
source backend/.venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

macOS ARM64 caveats (do NOT apply to x86_64):
- `cadquery` works in a **native** venv but not in ARM64 Linux containers
  (no wheel). The script installs it natively; STEP parsing then works.
- The Celery worker must use `--pool=solo` so PyTorch MPS (Apple GPU) can
  initialise (it SIGABRTs in a forked prefork worker). x86_64/CUDA/CPU are
  fork-safe and keep the default prefork pool.

## Why the export toolchain is pinned

Ultralytics will, on first TFLite export, try to `pip install` its export
deps (`tf_keras`, `onnx_graphsurgeon`, `ai-edge-litert`, a specific `onnx`
range, …). That auto-install needs internet and a `pip` on the process PATH —
it **fails inside a uvicorn/celery process**, surfacing one missing module at
a time. Pinning the whole set in `requirements.txt` removes the runtime
install entirely: the image/venv is complete and offline-reproducible.

Verified-working set: `tensorflow 2.21.0`, `tf-keras 2.21.0`, `onnx 1.19.1`,
`onnx2tf 1.28.8`, `onnxslim 0.1.94`, `onnxruntime 1.26.0`, `sng4onnx 2.0.1`,
`onnx-graphsurgeon 0.6.1`, `ai-edge-litert 1.3.0`, `numpy 2.1.3`.
