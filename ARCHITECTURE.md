# YOLO Assembly Vision - Technical Architecture

**Last Updated:** 2025-12-03
**Version:** 1.0
**Status:** Design Phase

---

## 🏛️ System Architecture Overview

This document outlines the technical architecture, design decisions, and rationale for the YOLO Assembly Vision platform.

---

## 📊 High-Level Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                          MOBILE APP LAYER                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Flutter Mobile App                          │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐    │   │
│  │  │ UI Layer   │  │ State Mgmt   │  │  Data Layer       │    │   │
│  │  │ (Screens)  │  │ (Riverpod)   │  │  (API Client)     │    │   │
│  │  └────────────┘  └──────────────┘  └───────────────────┘    │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐    │   │
│  │  │  Camera    │  │ TFLite Model │  │  Local Storage    │    │   │
│  │  │  Pipeline  │  │  Inference   │  │  (SQLite/Hive)    │    │   │
│  │  └────────────┘  └──────────────┘  └───────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
             REST API       WebSocket/SSE      File Upload
             (HTTPS)                           (Multipart)
                    │               │               │
┌───────────────────┴───────────────┴───────────────┴───────────────────┐
│                        API GATEWAY LAYER                               │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                   FastAPI Application                          │    │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐     │    │
│  │  │  Auth      │  │  File Upload │  │  Job Management  │     │    │
│  │  │  (JWT)     │  │  Handler     │  │  API             │     │    │
│  │  └────────────┘  └──────────────┘  └──────────────────┘     │    │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐     │    │
│  │  │  WebSocket │  │  Model Mgmt  │  │  Metrics API     │     │    │
│  │  │  Server    │  │  API         │  │                  │     │    │
│  │  └────────────┘  └──────────────┘  └──────────────────┘     │    │
│  └──────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              SQL Queries      Job Queue      File Storage
                    │               │               │
┌───────────────────┴───────────────┴───────────────┴───────────────────┐
│                       DATA PERSISTENCE LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐       │
│  │  PostgreSQL  │  │  Redis       │  │  File Storage        │       │
│  │  Database    │  │  (Cache +    │  │  (S3/MinIO/Local)    │       │
│  │              │  │   Broker)    │  │                      │       │
│  └──────────────┘  └──────────────┘  └──────────────────────┘       │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                            Celery Task Queue
                                    │
┌───────────────────────────────────┴───────────────────────────────────┐
│                      PROCESSING WORKER LAYER                           │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Celery Workers                              │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │    │
│  │  │  Blender        │  │  YOLO Training  │  │  Model      │  │    │
│  │  │  Rendering      │  │  Worker         │  │  Conversion │  │    │
│  │  │  Worker         │  │                 │  │  Worker     │  │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              External Dependencies                             │    │
│  │  • Blender 4.5+ (Python API)                                  │    │
│  │  • Ultralytics YOLO (PyTorch)                                 │    │
│  │  • coremltools (Core ML export)                               │    │
│  │  • TensorFlow Lite (TFLite export)                            │    │
│  └──────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Design Decisions & Rationale

### 1. **Why FastAPI over Flask/Django?**

**Decision:** Use FastAPI as the backend framework

**Rationale:**
- ✅ **Async Support:** Native async/await for handling concurrent requests efficiently
- ✅ **Auto Documentation:** Automatic OpenAPI (Swagger) docs generation
- ✅ **Type Safety:** Pydantic models provide runtime validation and IDE autocomplete
- ✅ **Performance:** Faster than Flask/Django (on par with Node.js/Go)
- ✅ **Modern:** Built on Starlette (ASGI) and Pydantic, designed for production

**Alternatives Considered:**
- **Flask:** Simpler but lacks async support and auto-docs
- **Django:** Feature-rich but heavier, overkill for API-only backend
- **Node.js/Express:** Good async but Python ecosystem needed for Blender/YOLO

**Trade-offs:**
- Steeper learning curve than Flask
- Smaller community than Django (but growing rapidly)

---

### 2. **Why PostgreSQL over MongoDB?**

**Decision:** Use PostgreSQL as the primary database

**Rationale:**
- ✅ **Relational Data:** User → Projects → Jobs → Models fits relational model well
- ✅ **ACID Compliance:** Strong consistency guarantees for critical operations
- ✅ **Mature Ecosystem:** Excellent ORM support (SQLAlchemy), monitoring tools
- ✅ **JSON Support:** JSONB type for flexible metadata storage
- ✅ **Full-Text Search:** Built-in search capabilities for logs/metadata

**Alternatives Considered:**
- **MongoDB:** Good for unstructured data, but overkill here
- **SQLite:** Great for local dev, but not production-ready for multi-user

**Trade-offs:**
- Requires schema migrations (Alembic)
- Slightly more complex setup than NoSQL

**Schema Design:**
```sql
-- Core tables
users (id, email, password_hash, quota_mb, created_at)
assembly_projects (id, user_id, name, file_path, status, metadata)
training_jobs (id, project_id, status, progress, config, created_at)
models (id, job_id, format, file_path, metrics, size_mb)

-- Indexes
idx_projects_user_id ON assembly_projects(user_id)
idx_jobs_project_id ON training_jobs(project_id)
idx_jobs_status ON training_jobs(status)
```

---

### 3. **Why Celery over Other Job Queues?**

**Decision:** Use Celery with Redis as the task queue

**Rationale:**
- ✅ **Python Native:** Seamless integration with Python backend
- ✅ **Battle-Tested:** Used by Instagram, Reddit, millions of jobs/day
- ✅ **Scalable:** Can scale to thousands of workers across machines
- ✅ **Flexible:** Supports priorities, retries, timeouts, chaining
- ✅ **Monitoring:** Flower dashboard for task inspection

**Alternatives Considered:**
- **RQ (Redis Queue):** Simpler but less feature-rich
- **Huey:** Lightweight but less mature
- **RabbitMQ + Kombu:** More complex setup

**Trade-offs:**
- More complex than RQ
- Requires Redis/RabbitMQ as broker

**Task Types:**
```python
# Rendering task (GPU-bound, long-running)
@celery_app.task(bind=True, time_limit=3600)
def render_synthetic_data(self, project_id: int, config: dict):
    # Blender rendering logic
    pass

# Training task (GPU-bound, very long-running)
@celery_app.task(bind=True, time_limit=7200)
def train_yolo_model(self, job_id: int, dataset_path: str):
    # YOLO training logic
    pass

# Conversion task (CPU-bound, medium duration)
@celery_app.task(bind=True, time_limit=600)
def convert_model(self, model_id: int, target_format: str):
    # Model conversion logic
    pass
```

---

### 4. **Why Flutter over React Native/Native?**

**Decision:** Use Flutter for cross-platform mobile app

**Rationale:**
- ✅ **Single Codebase:** One codebase for iOS + Android (faster development)
- ✅ **Performance:** Compiled to native ARM code (near-native speed)
- ✅ **UI Consistency:** Pixel-perfect UI across platforms
- ✅ **Hot Reload:** Fast iteration during development
- ✅ **Growing Ecosystem:** Excellent packages for camera, ML, networking

**Alternatives Considered:**
- **Native iOS (Swift):** Best performance but iOS-only, doubles dev time
- **React Native:** Larger ecosystem but bridge performance issues for ML
- **Xamarin:** C# ecosystem, less popular, poorer ML support

**Trade-offs:**
- Larger app size (~20MB base vs ~5MB native)
- Slightly lower performance than pure native (negligible for this use case)

**State Management Choice: Riverpod**
- Modern, compile-safe alternative to Provider
- Better testability than Bloc
- Less boilerplate than Redux

---

### 5. **Why TensorFlow Lite over ONNX/PyTorch Mobile?**

**Decision:** Use TensorFlow Lite for mobile inference (+ Core ML for iOS)

**Rationale:**
- ✅ **Cross-Platform:** TFLite works on iOS + Android
- ✅ **Optimized:** Designed for mobile/edge devices
- ✅ **Small Size:** Models typically 10-50MB
- ✅ **Hardware Acceleration:** GPU delegates for iOS/Android
- ✅ **Mature:** Battle-tested, excellent documentation

**Alternatives Considered:**
- **ONNX Runtime:** Good but less mobile-optimized
- **PyTorch Mobile:** Less mature, larger model sizes
- **Core ML only:** iOS-only, would need separate Android solution

**Dual Model Strategy:**
```
iOS: Core ML (.mlpackage) - Best performance on Neural Engine
Android: TFLite (.tflite) - Best compatibility
```

**Trade-offs:**
- Requires model conversion (PyTorch → TFLite/CoreML)
- Potential accuracy loss during quantization (FP32 → FP16)

---

### 6. **File Storage Strategy**

**Decision:** Support multiple storage backends (Local FS, MinIO, S3)

**Rationale:**
- ✅ **Flexibility:** Users can choose based on their deployment
- ✅ **Cost:** Local FS is free, S3 is ~$0.023/GB/month
- ✅ **Scalability:** S3/MinIO scale infinitely
- ✅ **Simple Abstraction:** Abstract storage interface for easy swapping

**Storage Types:**
```python
# Abstract storage interface
class StorageBackend(ABC):
    @abstractmethod
    def upload(self, file: bytes, path: str) -> str:
        pass

    @abstractmethod
    def download(self, path: str) -> bytes:
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        pass

# Implementations
class LocalFileStorage(StorageBackend): ...
class MinIOStorage(StorageBackend): ...
class S3Storage(StorageBackend): ...
```

**File Organization:**
```
storage/
├── uploads/{user_id}/{project_id}/
│   └── assembly.blend
├── datasets/{project_id}/
│   ├── images/
│   └── labels/
└── models/{model_id}/
    ├── model.pt
    ├── model.tflite
    └── model.mlpackage/
```

---

### 7. **Authentication & Security**

**Decision:** JWT tokens with refresh token rotation

**Rationale:**
- ✅ **Stateless:** No server-side session storage needed
- ✅ **Scalable:** Works across multiple API servers
- ✅ **Secure:** Short-lived access tokens (15 min) + long-lived refresh tokens (7 days)
- ✅ **Standard:** Industry-standard approach

**Authentication Flow:**
```
1. User logs in → Server returns access_token (15min) + refresh_token (7d)
2. App stores tokens securely (flutter_secure_storage)
3. Every API call includes: Authorization: Bearer <access_token>
4. When access_token expires → Use refresh_token to get new pair
5. On logout → Invalidate refresh_token (blacklist in Redis)
```

**Security Measures:**
- Password hashing: bcrypt (cost factor 12)
- Rate limiting: 100 requests/min per IP
- File upload limits: 500MB max
- Input validation: Pydantic schemas
- SQL injection protection: SQLAlchemy parameterized queries
- XSS protection: Auto-escaping in responses
- HTTPS enforcement: Redirect HTTP → HTTPS

---

### 8. **Connectivity Options Architecture**

**Decision:** Support 3 connectivity modes (Direct IP, ngrok, VPN)

**Rationale:**
- ✅ **Flexibility:** Users choose based on their network setup
- ✅ **No Vendor Lock-In:** Not dependent on any cloud service
- ✅ **Privacy:** VPN option for maximum privacy
- ✅ **Ease of Use:** ngrok for zero-config remote access

**Connectivity Modes:**

#### Mode A: Direct IP (Local Network)
```
Mobile App ──(HTTP/HTTPS)──> Server (192.168.1.x:8000)
```
- **Pros:** Lowest latency, no third-party dependencies
- **Cons:** Requires port forwarding for remote access, dynamic IP issues

#### Mode B: ngrok Tunnel
```
Mobile App ──(HTTPS)──> ngrok Cloud ──> Server (localhost:8000)
```
- **Pros:** Zero network configuration, HTTPS included, works anywhere
- **Cons:** Latency overhead (~50-100ms), ngrok dependency, $8/month for custom domain

#### Mode C: VPN (Netbird/Tailscale)
```
Mobile App ──(VPN Encrypted)──> Server (100.x.x.x:8000)
```
- **Pros:** Secure, direct connection, works across networks
- **Cons:** Requires VPN setup on both devices, slightly complex for non-technical users

**Implementation:**
```dart
// Flutter app - Server configuration
class ServerConfig {
  final String baseUrl;  // Can be IP, domain, or ngrok URL
  final ConnectionType type;

  enum ConnectionType { direct, ngrok, vpn }
}

// Auto-discovery for direct mode (mDNS/Bonjour)
Future<String?> discoverLocalServer() async {
  // Broadcast UDP packet on 255.255.255.255:8000
  // Server responds with its IP
}
```

---

### 9. **Real-Time Updates Architecture**

**Decision:** Use Server-Sent Events (SSE) over WebSockets

**Rationale:**
- ✅ **Simpler:** SSE is one-way (server → client), easier to implement
- ✅ **Auto-Reconnect:** Built-in reconnection in SSE protocol
- ✅ **HTTP-Friendly:** Works with standard HTTP, easier with proxies/firewalls
- ✅ **Sufficient:** We only need server → client updates (job progress)

**Alternatives Considered:**
- **WebSockets:** Bidirectional, but overkill for our use case
- **Polling:** Simple but inefficient (wasted bandwidth)

**SSE Implementation:**
```python
# FastAPI endpoint
@app.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: int):
    async def event_generator():
        while True:
            job = await get_job(job_id)
            yield {
                "event": "progress",
                "data": json.dumps({
                    "progress": job.progress,
                    "status": job.status,
                    "metrics": job.metrics
                })
            }
            if job.status in ["complete", "failed"]:
                break
            await asyncio.sleep(2)  # Update every 2 seconds

    return EventSourceResponse(event_generator())
```

```dart
// Flutter client
final sseClient = SseClient('$baseUrl/jobs/$jobId/stream');
sseClient.stream.listen((event) {
  final data = json.decode(event.data);
  updateUI(data['progress'], data['status']);
});
```

---

### 10. **Model Training Strategy**

**Decision:** Use Ultralytics YOLOv8/v11 with default hyperparameters

**Rationale:**
- ✅ **Ease of Use:** Simplest YOLO API (one-liner training)
- ✅ **Performance:** State-of-the-art accuracy
- ✅ **AutoML:** Automatic hyperparameter optimization
- ✅ **Mobile-Friendly:** Nano/small models run well on mobile

**Training Configuration:**
```python
from ultralytics import YOLO

# Default training config (good for most cases)
model = YOLO('yolov8n.pt')  # Nano model (smallest)
results = model.train(
    data='dataset.yaml',
    epochs=100,              # Auto early-stopping
    imgsz=640,              # Standard input size
    batch=16,               # Adjust based on GPU
    device='0',             # GPU 0
    workers=8,              # Data loading threads
    patience=20,            # Early stopping patience
    save_period=10,         # Save checkpoint every 10 epochs
    cache=True,             # Cache images in RAM (faster)
    augment=True,           # Use default augmentations
)

# Export to mobile formats
model.export(format='tflite', int8=False)  # FP16 quantization
model.export(format='coreml', nms=True)    # Core ML with NMS
```

**Model Variants:**
| Variant | Params | Size | Inference Time (Mobile) | Use Case |
|---------|--------|------|-------------------------|----------|
| YOLOv8n | 3.2M   | 6MB  | 30-40 FPS               | Real-time on phone |
| YOLOv8s | 11.2M  | 22MB | 20-25 FPS               | Better accuracy |
| YOLOv8m | 25.9M  | 50MB | 10-15 FPS               | High accuracy |

**Recommendation:** Start with YOLOv8n, upgrade to YOLOv8s if accuracy insufficient

---

## 🔄 Data Flow Diagrams

### User Workflow: Upload → Train → Detect

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. UPLOAD PHASE                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User selects 3D file (assembly.blend)                         │
│       │                                                         │
│       ├─> Flutter app uploads to API (multipart/form-data)     │
│       │                                                         │
│       └─> API validates file (type, size)                      │
│                │                                                │
│                ├─> Save to storage (S3/Local)                  │
│                │                                                │
│                └─> Create AssemblyProject record in DB         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. RENDERING PHASE                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User clicks "Generate Dataset"                                │
│       │                                                         │
│       ├─> API creates TrainingJob (status=PENDING)             │
│       │                                                         │
│       └─> Enqueue Celery task: render_synthetic_data()         │
│                │                                                │
│                ├─> Celery worker picks up task                 │
│                │                                                │
│                ├─> Launch Blender subprocess                    │
│                │        │                                       │
│                │        ├─> Import 3D file                      │
│                │        ├─> Set up scene (camera, lights)      │
│                │        ├─> Render N images with randomization │
│                │        └─> Generate YOLO labels                │
│                │                                                │
│                ├─> Save dataset to storage                      │
│                │                                                │
│                └─> Update job status (COMPLETE)                │
│                                                                 │
│  (User sees progress via SSE: 10%, 20%, ..., 100%)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. TRAINING PHASE                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User clicks "Train Model"                                      │
│       │                                                         │
│       ├─> API updates TrainingJob (status=TRAINING)            │
│       │                                                         │
│       └─> Enqueue Celery task: train_yolo_model()              │
│                │                                                │
│                ├─> Celery worker picks up task                 │
│                │                                                │
│                ├─> Load dataset from storage                    │
│                │                                                │
│                ├─> Train YOLO model (Ultralytics)              │
│                │        │                                       │
│                │        └─> Stream metrics to DB (mAP, loss)   │
│                │                                                │
│                ├─> Save trained model (.pt)                     │
│                │                                                │
│                └─> Update job status (TRAINED)                 │
│                                                                 │
│  (User sees metrics via SSE: Epoch 1/100, mAP=0.45, ...)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. CONVERSION PHASE                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  System auto-triggers conversion after training                │
│       │                                                         │
│       └─> Enqueue Celery task: convert_model()                 │
│                │                                                │
│                ├─> Convert to TFLite (Android)                 │
│                │        │                                       │
│                │        └─> Quantize to FP16                    │
│                │                                                │
│                ├─> Convert to Core ML (iOS)                     │
│                │        │                                       │
│                │        └─> Optimize for Neural Engine         │
│                │                                                │
│                ├─> Validate converted models                    │
│                │                                                │
│                └─> Create Model records in DB                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 5. DEPLOYMENT PHASE                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User clicks "Download Model" in app                            │
│       │                                                         │
│       ├─> API serves model file (GET /models/{id}/download)    │
│       │                                                         │
│       ├─> App downloads model (progress bar)                   │
│       │                                                         │
│       └─> App stores model locally                             │
│                │                                                │
│                └─> Model ready for inference                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 6. INFERENCE PHASE                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User opens camera view                                         │
│       │                                                         │
│       ├─> Load TFLite model into interpreter                   │
│       │                                                         │
│       ├─> Start camera (30 FPS)                                │
│       │        │                                                │
│       │        └─> For each frame:                             │
│       │                 │                                       │
│       │                 ├─> Preprocess (resize, normalize)     │
│       │                 ├─> Run inference                       │
│       │                 ├─> Postprocess (NMS, threshold)       │
│       │                 └─> Render bounding boxes               │
│       │                                                         │
│       └─> Display real-time detections                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack Summary

### Backend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.104+ | REST API server |
| Database | PostgreSQL | 15+ | Primary data store |
| Cache/Broker | Redis | 7+ | Celery broker + caching |
| Task Queue | Celery | 5.3+ | Async job processing |
| ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Migrations | Alembic | 1.12+ | Schema versioning |
| Auth | python-jose | 3.3+ | JWT token handling |
| Validation | Pydantic | 2.0+ | Request/response validation |

### Machine Learning
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Training | Ultralytics YOLO | 8.0+ | Object detection training |
| Rendering | Blender | 4.5+ | Synthetic data generation |
| PyTorch | PyTorch | 2.1+ | Deep learning framework |
| Core ML Export | coremltools | 7.0+ | iOS model conversion |
| TFLite Export | TensorFlow | 2.14+ | Android model conversion |

### Mobile App
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Flutter | 3.16+ | Cross-platform UI |
| State Management | Riverpod | 2.4+ | App state |
| HTTP Client | Dio | 5.4+ | API communication |
| ML Inference | tflite_flutter | 0.10+ | On-device inference |
| Camera | camera | 0.10+ | Camera capture |
| Local Storage | Hive | 2.2+ | Offline data |
| Secure Storage | flutter_secure_storage | 9.0+ | Token storage |

### DevOps
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Containerization | Docker | 24+ | Application packaging |
| Orchestration | Docker Compose | 2.23+ | Multi-container apps |
| CI/CD | GitHub Actions | - | Automated testing/deployment |
| Monitoring | Prometheus + Grafana | - | Metrics & dashboards |
| Logging | Loguru | 0.7+ | Structured logging |

---

## 📈 Performance Targets

### Backend API
- **Response Time:** <200ms (p95) for CRUD operations
- **File Upload:** Support 500MB files in <5 min (on 10 Mbps upload)
- **Concurrent Users:** Handle 50 concurrent users smoothly
- **Job Throughput:** Process 5-10 jobs/hour (depending on GPU)

### Rendering Pipeline
- **Time:** Generate 500-image dataset in <10 minutes
- **Memory:** Keep Blender memory usage <6GB
- **Quality:** Produce valid YOLO labels for >95% of images

### Training Pipeline
- **Time:** Train model on 500 images in <30 minutes (RTX 3060)
- **Accuracy:** Achieve >80% mAP50 on validation set
- **Conversion:** Complete TFLite + CoreML conversion in <5 minutes

### Mobile App
- **Inference:** >20 FPS on mid-range phones (iPhone 12, Galaxy S21)
- **Model Download:** <2 minutes on 4G connection (50MB model)
- **App Size:** Keep total app size <100MB
- **Battery:** <5% battery drain per 10 min of inference

---

## 🔐 Security Considerations

### API Security
- ✅ JWT tokens with short expiry (15 min)
- ✅ Refresh token rotation on use
- ✅ Rate limiting (100 req/min per IP)
- ✅ Input validation on all endpoints
- ✅ SQL injection protection (parameterized queries)
- ✅ XSS prevention (auto-escaping)
- ✅ HTTPS enforcement

### File Upload Security
- ✅ File type validation (magic number check, not just extension)
- ✅ File size limits (500MB max)
- ✅ Malware scanning (ClamAV integration optional)
- ✅ Sandboxed Blender execution (isolated subprocess)
- ✅ Quota enforcement (storage limits per user)

### Mobile Security
- ✅ Secure token storage (flutter_secure_storage)
- ✅ Certificate pinning (optional for HTTPS)
- ✅ Model integrity checks (SHA256 checksums)
- ✅ No sensitive data in logs

---

## 🚀 Scalability Strategy

### Horizontal Scaling (10 → 100 → 1000 users)

#### Stage 1: Single Server (0-50 users)
```
[API + Worker + DB + Redis] on one machine
```
- Sufficient for MVP and early adopters
- Cost: $0-50/month (self-hosted)

#### Stage 2: Separated Services (50-200 users)
```
[API Server] + [Worker Server(s)] + [Managed DB + Redis]
```
- Separate worker machines for GPU tasks
- Managed PostgreSQL (AWS RDS/Azure DB)
- Managed Redis (AWS ElastiCache)
- Cost: $150-300/month

#### Stage 3: Multi-Region + Load Balancing (200-1000 users)
```
[Load Balancer] → [API Cluster] + [Worker Pool] + [Distributed DB]
```
- Multiple API instances behind load balancer (ALB/NGINX)
- Autoscaling worker pool (Kubernetes)
- Database read replicas
- CDN for model distribution (CloudFront)
- Cost: $500-1500/month

---

## 📊 Monitoring & Observability

### Key Metrics to Track

#### Backend Metrics
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database connection pool usage
- Celery queue length (pending tasks)

#### Worker Metrics
- Job completion rate
- Job failure rate
- Average rendering time
- Average training time
- GPU utilization (%)
- Memory usage

#### Mobile Metrics
- App crash rate
- Inference FPS
- Model download success rate
- API call success rate
- Battery drain

### Logging Strategy
```python
# Structured logging with context
logger.info("Training started", extra={
    "job_id": job.id,
    "user_id": job.user_id,
    "dataset_size": dataset.num_images,
    "model_type": "yolov8n"
})
```

---

## 🎓 Future Architecture Enhancements

### Phase 2+ Features
- **Distributed Training:** Multi-GPU training across nodes
- **Model Versioning:** Track model lineage (A/B testing)
- **Feature Store:** Centralized dataset management
- **Auto-Scaling:** Dynamic worker scaling based on queue length
- **Multi-Tenancy:** Isolated environments per organization
- **Federated Learning:** Train on user devices (privacy-preserving)

---

**Next Step:** Review this architecture and start implementation (see TODO.md)
