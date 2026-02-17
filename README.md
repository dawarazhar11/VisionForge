<div align="center">

# VisionForge

**End-to-end synthetic data generation, YOLO model training, and mobile deployment platform for real-time object detection.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.123+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.16+-02569B.svg?logo=flutter&logoColor=white)](https://flutter.dev)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.9+-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)

[Getting Started](#getting-started) · [Architecture](#architecture) · [Documentation](#documentation) · [Contributing](#contributing)

</div>

---

## Overview

VisionForge automates the entire computer vision pipeline -- from generating synthetic training data using Blender 3D renders, to training custom YOLO object detection models, to deploying them on mobile devices for real-time inference.

Upload a 3D assembly file, generate hundreds of labeled training images automatically, train a detection model, and deploy it to iOS or Android -- all through a unified API and mobile app.

### Key Capabilities

- **Synthetic Data Generation** -- Render labeled training images from 3D models using Blender with randomized camera angles, lighting, and object visibility
- **Automated YOLO Training** -- Train YOLOv8/v11 segmentation models on generated datasets with GPU acceleration
- **Multi-Platform Export** -- Convert trained models to CoreML (iOS), TFLite (Android), and ONNX (desktop/edge)
- **Real-Time Mobile Inference** -- Run object detection at 30+ FPS on-device via Flutter cross-platform app
- **RESTful API** -- Full project management, job tracking, and model serving through FastAPI
- **Async Processing** -- Background rendering and training jobs via Celery + Redis task queue

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Upload 3D  │────>│  Generate   │────>│  Train YOLO │────>│   Deploy    │
│  Assembly   │     │  Synthetic  │     │    Model    │     │  to Mobile  │
│   (.blend)  │     │   Dataset   │     │  (GPU/CPU)  │     │  (iOS/And)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                     Blender EEVEE       Ultralytics         CoreML/TFLite
                     150+ images         YOLOv8/v11          30+ FPS
                     YOLO labels         mAP tracking        On-device
```

**Workflow:**

1. **Upload** a Blender `.blend` file (or `.obj`, `.stl`, `.fbx`) via API or mobile app
2. **Render** synthetic training data -- Blender generates images with randomized camera angles, lighting conditions, and YOLO-format bounding box labels
3. **Train** a YOLO model on the generated dataset with configurable epochs, image size, and model architecture
4. **Export** the trained model to CoreML (iOS), TFLite (Android), or ONNX
5. **Deploy** to your mobile device and run real-time object detection through the camera

## Detection Classes

The system detects 7 mechanical component classes in assembly scenes:

| Class ID | Name | Description |
|----------|------|-------------|
| 0 | `small_screw` | Standard small screws (11 instances) |
| 1 | `small_hole` | Screw position indicators / bracket holes |
| 2 | `large_screw` | Larger structural screws (left & right) |
| 3 | `large_hole` | Large screw mounting holes |
| 4 | `bracket_A` | Keyhole bracket type A |
| 5 | `bracket_B` | Keyhole bracket type B |
| 6 | `surface` | Main body / empty surface area |

## Project Structure

```
.
├── backend/                 # FastAPI backend server
│   ├── app/
│   │   ├── api/             # REST API endpoints (auth, projects, jobs, models)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response validation
│   │   ├── services/        # Business logic layer
│   │   ├── workers/         # Celery async task definitions
│   │   ├── blender/         # Blender subprocess integration
│   │   ├── middleware/      # Rate limiting, auth middleware
│   │   └── main.py          # FastAPI application entry point
│   ├── alembic/             # Database migrations
│   ├── tests/               # Unit and integration tests
│   ├── Dockerfile           # Backend container image
│   └── requirements.txt     # Python dependencies
│
├── flutter_app/             # Cross-platform mobile app (iOS & Android)
│   ├── lib/
│   │   ├── screens/         # 19 screen components (camera, projects, training)
│   │   ├── services/        # API client, YOLO inference engine
│   │   ├── providers/       # Riverpod state management
│   │   ├── models/          # Data models
│   │   └── widgets/         # Reusable UI components
│   └── pubspec.yaml         # Flutter dependencies
│
├── blender/                 # Blender rendering pipeline
│   ├── eevee_desk_scene17_dualpass.py   # Main synthetic data generation script
│   └── eevee_api_wrapper.py             # Environment-configurable render wrapper
│
├── training/                # ML training utilities
│   ├── train_yolo_model.py              # YOLO training + CoreML/TFLite export
│   ├── analyze_detection_results.py     # Dataset analysis and debugging
│   ├── setup_training_env.py            # Environment validation and setup
│   └── test_enhanced_script.py          # Blender script validation tests
│
├── scripts/                 # Platform helper scripts
│   ├── docker/              # Docker lifecycle management (.bat)
│   ├── podman/              # Podman lifecycle management (.bat)
│   ├── setup/               # Environment setup (Blender, venv, Xcode)
│   └── training/            # Training workflow automation (.bat)
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # System design and technical decisions
│   ├── ROADMAP.md           # Product roadmap and milestones
│   ├── DEPLOYMENT.md        # Production deployment guide
│   ├── DOCKER_GUIDE.md      # Docker setup and usage
│   ├── PODMAN_GUIDE.md      # Podman alternative setup
│   ├── COMPLETE_WORKFLOW.md # End-to-end usage walkthrough
│   ├── MODEL_RETRAINING_GUIDE.md  # Model retraining procedures
│   └── ...                  # Additional guides
│
├── yolo_assembly_app/       # Legacy Flutter app (older version)
├── yolo-ios-app/            # Native Swift iOS app
├── docker-compose.yml       # Full stack container orchestration
├── LICENSE                  # MIT License
└── README.md
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Server** | FastAPI 0.123+ | Async REST API with auto-generated docs |
| **Database** | PostgreSQL 15 + SQLAlchemy 2.0 | Persistent storage with ORM |
| **Task Queue** | Celery 5.6 + Redis 7 | Async rendering and training jobs |
| **ML Framework** | Ultralytics YOLO + PyTorch 2.9 | Model training and inference |
| **3D Rendering** | Blender 4.5 (EEVEE) | Synthetic data generation |
| **Mobile App** | Flutter 3.16+ (Dart) | Cross-platform iOS/Android client |
| **On-Device ML** | tflite_flutter / CoreML | Real-time mobile inference |
| **Auth** | JWT (python-jose + bcrypt) | Token-based authentication |
| **Containers** | Docker / Docker Compose | Development and production deployment |

## Getting Started

### Prerequisites

- Python 3.8+
- [Blender 4.5+](https://www.blender.org/download/) (for synthetic data generation)
- Docker & Docker Compose (recommended for backend)
- Flutter 3.16+ (for mobile app)
- NVIDIA GPU with CUDA (recommended for training)

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/dawarazhar11/yolo-computer-vision-baseline.git
cd yolo-computer-vision-baseline

# Start all services (API, PostgreSQL, Redis, Celery)
docker compose up -d

# API available at http://localhost:8002
# API docs at http://localhost:8002/docs
```

### Manual Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Set up environment variables
cp backend/.env.example backend/.env
# Edit .env with your database credentials

# Run database migrations
cd backend && alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### Generate Synthetic Data

```bash
# Using the Blender CLI (from project root)
blender "your_scene.blend" --background --python blender/eevee_desk_scene17_dualpass.py

# Or with custom configuration via environment variables
BLENDER_NUM_RENDERS=200 BLENDER_RESOLUTION_X=1280 BLENDER_RESOLUTION_Y=720 \
  blender "your_scene.blend" --background --python blender/eevee_api_wrapper.py
```

### Train a Model

```bash
# Set up training environment
python training/setup_training_env.py

# Run the training pipeline (dataset setup + train + export)
python training/train_yolo_model.py
```

### Flutter Mobile App

```bash
cd flutter_app

# Install dependencies
flutter pub get

# Run on connected device
flutter run
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Create user account |
| `POST` | `/api/v1/auth/login` | Authenticate and get JWT tokens |
| `POST` | `/api/v1/projects/upload` | Upload 3D assembly file |
| `GET` | `/api/v1/projects` | List projects with pagination |
| `POST` | `/api/v1/jobs` | Create rendering/training job |
| `GET` | `/api/v1/jobs/{id}/stream` | SSE real-time job progress |
| `GET` | `/api/v1/models` | List trained models |
| `GET` | `/api/v1/models/{id}/download` | Download model for deployment |
| `GET` | `/api/v1/monitoring/health` | System health check |

Full interactive API docs available at `/docs` (Swagger UI) when the server is running.

## Infrastructure

```bash
docker compose up -d
```

| Service | Port | Purpose |
|---------|------|---------|
| `backend` | 8002 | FastAPI REST API |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Cache & Celery message broker |
| `celery_worker` | -- | Async task processing (render, train, export) |
| `celery_beat` | -- | Scheduled job runner |
| `portainer` | 9000 | Container management UI |

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, technical decisions, data flow |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment guide |
| [Docker Guide](docs/DOCKER_GUIDE.md) | Docker setup and container management |
| [Podman Guide](docs/PODMAN_GUIDE.md) | Podman alternative to Docker |
| [Complete Workflow](docs/COMPLETE_WORKFLOW.md) | End-to-end usage walkthrough |
| [Model Retraining](docs/MODEL_RETRAINING_GUIDE.md) | How to retrain and update models |
| [Flutter Implementation](docs/FLUTTER_IMPLEMENTATION.md) | Mobile app architecture |
| [Roadmap](docs/ROADMAP.md) | Planned features and milestones |
| [Platform Requirements](docs/PLATFORM_REQUIREMENTS.md) | System requirements by platform |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dawarazhar11/yolo-computer-vision-baseline&type=Date)](https://star-history.com/#dawarazhar11/yolo-computer-vision-baseline&Date)
