<div align="center">

# VisionForge

**Turn any 3D design file into a deployable, real-time object-detection model — no manual labeling.**

Upload a CAD assembly or Blender scene → VisionForge auto-generates labeled synthetic training images → trains a YOLO model → exports it to mobile → detects on-device.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.123-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.16+-02569B.svg?logo=flutter&logoColor=white)](https://flutter.dev)
[![Ultralytics YOLO](https://img.shields.io/badge/YOLO-Ultralytics-purple.svg)](https://docs.ultralytics.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)

[Quick Start](#quick-start) · [How It Works](#how-it-works) · [Architecture](#architecture) · [Setup](docs/SETUP.md) · [Documentation](#documentation)

</div>

---

## Overview

Training an object detector normally means collecting and hand-labeling thousands of photos. VisionForge removes that step entirely: it renders **automatically labeled** training images from a 3D model you already have, trains a detector on them, and packages the result for on-device inference.

The key idea is that **labels come from the design file itself.** The names of the parts in your CAD assembly or Blender scene become the detection classes — nothing is hardcoded. Name a part `gear_housing` and the model learns to detect `gear_housing`.

### Capabilities

- **Any design file in** — `.step` / `.stp`, `.blend`, `.obj`, `.stl`, `.fbx`
- **Automatic labeling** — Blender renders images from randomized camera angles and lighting, emitting YOLO bounding boxes with zero manual annotation
- **Dynamic classes** — detection labels are derived from the model: CAD component names (Fusion 360 / SolidWorks / Inventor), Blender object names, or recognized STEP features (holes, bosses, chamfers). Overridable per project.
- **Annotated previews** — every render job produces preview images with boxes drawn on, so you can verify the dataset
- **YOLO training** — Ultralytics YOLO11 with automatic CUDA → MPS → CPU device selection
- **Mobile export** — TFLite (Android) and CoreML (iOS), served with a matching `labels.txt`
- **On-device inference** — a Flutter app runs the trained model live through the camera
- **Async by design** — FastAPI + Celery + Redis process render and training jobs in the background with live progress (polling or SSE)

## How It Works

```
┌──────────────┐    ┌───────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  Upload      │──> │  Auto-render  │──> │  Train YOLO  │──> │  Export      │──> │  Detect     │
│  design file │    │  + auto-label │    │  model       │    │  TFLite/     │    │  on-device  │
│  (STEP/.blend)│   │  (Blender)    │    │ (Ultralytics)│    │  CoreML      │    │  (Flutter)  │
└──────────────┘    └───────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
        classes resolved from the design file ───────────────────────────> served as labels.txt
```

1. **Upload** a 3D file through the app or API.
2. **Render** — Blender (headless EEVEE) generates synthetic images with randomized camera/lighting and writes YOLO labels. Classes are resolved from the file (CAD part names, STEP features, or mesh names); annotated previews are generated for review.
3. **Train** — a YOLO model trains on the dataset, carrying those class names end-to-end.
4. **Export** — the trained model is converted to TFLite/CoreML and bundled with its labels.
5. **Deploy** — download the model into the Flutter app, set it active, and detect through the camera.

## Quick Start

### Docker (recommended — Linux / Windows x86_64)

On x86_64 the entire stack runs in containers, including STEP feature recognition.

```bash
git clone https://github.com/dawarazhar11/VisionForge.git
cd VisionForge

docker compose up -d --build
docker compose exec backend alembic upgrade head     # first boot only

# API docs: http://localhost:8002/docs
```

Verify every dependency (including the TFLite export toolchain) is present:

```bash
docker compose exec backend python -c "import tensorflow, tf_keras, onnx, onnx2tf, ai_edge_litert, cadquery, ultralytics; print('OK')"
```

### Native (macOS / Linux without Docker)

```bash
scripts/setup/setup_backend.sh        # one-shot venv + full install + verification
source backend/.venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

See **[docs/SETUP.md](docs/SETUP.md)** for platform specifics (macOS ARM64 notes, why the export toolchain is pinned, GPU/MPS handling).

### Mobile app

```bash
cd flutter_app
flutter pub get
flutter run            # debug on a connected device/simulator
```

Set the backend URL on the login screen, sign in, then: **New Project → upload → render → train → download model → Detect**.

## Architecture

**Monorepo layout**

```
backend/        FastAPI API + Celery workers (auth, projects, jobs, models, monitoring)
  app/api/        REST route handlers
  app/workers/    Celery render & training tasks
  app/blender/    Blender subprocess integration + class-map resolution
  app/services/   STEP parsing (cadquery/XDE), preview generation, storage
  app/training/   YOLO training + multi-format export
blender/        Headless render scripts (generic .blend, STEP parts, STEP features)
flutter_app/    Cross-platform mobile client (camera, projects, training, models)
training/       Standalone training/analysis utilities
scripts/        Setup, Docker/Podman lifecycle, and E2E validation
docs/           Architecture, setup, and workflow guides
```

**Services** (`docker compose`): `backend:8002`, `postgres`, `redis`, `celery_worker`, `celery_beat`.

**Class resolution** (the heart of the dynamic-label system):

| Source | Becomes classes |
|--------|-----------------|
| STEP assembly with named components | One class per CAD part name |
| STEP single part | Recognized features (`hole`, `boss`, `chamfer`, `planar_face`) |
| `.blend` / mesh files | One class per named mesh object |
| Project override | A custom `class_map` set via the API/app |

Class names flow from the render job → training → the served `labels.txt`, so the model, the API, and the app always agree on what each detection means.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Uvicorn |
| Async jobs | Celery, Redis |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| 3D / rendering | Blender (headless EEVEE) |
| CAD parsing | cadquery / OpenCASCADE (XDE) |
| ML | Ultralytics YOLO11, PyTorch |
| Export | TensorFlow + ONNX toolchain → TFLite, CoreML |
| Mobile | Flutter, tflite_flutter |
| Auth | JWT (HS256), bcrypt |

## Documentation

| Document | Description |
|----------|-------------|
| [Setup](docs/SETUP.md) | Install paths, dependency reproducibility, platform notes |
| [Architecture](docs/ARCHITECTURE.md) | System design and data flow |
| [Flutter Revamp](docs/FLUTTER_REVAMP.md) | Mobile app architecture |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment |
| [Complete Workflow](docs/COMPLETE_WORKFLOW.md) | End-to-end walkthrough |
| [Platform Requirements](docs/PLATFORM_REQUIREMENTS.md) | Requirements by platform |

## Project Status

The end-to-end pipeline — upload → render → train → export → on-device detection — is implemented and validated. Detection quality depends on the training data: a model is only as good as the renders it learns from (more images, realistic materials, and more epochs improve real-world accuracy).

## License

MIT — see [LICENSE](LICENSE).
