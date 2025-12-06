# YOLO Assembly Vision - Product Roadmap

## 🎯 Vision Statement

A complete SaaS platform where users can upload 3D assembly files from their mobile device, automatically generate synthetic training data, train custom YOLO models on a backend server, and deploy those models for real-time object detection on their mobile device.

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUTTER MOBILE APP                          │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐        │
│  │  Camera    │  │   Upload    │  │   Model Status   │        │
│  │  Inference │  │  Assembly   │  │   & Management   │        │
│  └────────────┘  └─────────────┘  └──────────────────┘        │
│         ▲                │                     ▲                │
│         │                │                     │                │
│         │ (WebSocket/SSE)│  (REST API)        │ (REST API)     │
│         └────────────────┼─────────────────────┘                │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           │ HTTPS / VPN / ngrok
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    BACKEND SERVER (Python)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI / Flask REST API                     │  │
│  │  • User authentication (JWT)                              │  │
│  │  • Assembly file upload & storage                         │  │
│  │  • Job submission & status tracking                       │  │
│  │  • Model versioning & deployment                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Job Queue (Celery + Redis/RabbitMQ)            │  │
│  │  • Async task processing                                  │  │
│  │  • Progress tracking                                      │  │
│  │  • Worker scaling                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌──────────────┬──────────┴──────────┬──────────────────────┐ │
│  │   Blender    │   YOLO Training    │   Model Conversion   │ │
│  │   Pipeline   │   (Ultralytics)    │   (CoreML/TFLite)    │ │
│  │  • Scene gen │   • AutoML         │   • Format export    │ │
│  │  • Rendering │   • Hyperparams    │   • Optimization     │ │
│  └──────────────┴────────────────────┴──────────────────────┘ │
│                            │                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Database (PostgreSQL/MongoDB)                │  │
│  │  • Users & authentication                                 │  │
│  │  • Assembly projects                                      │  │
│  │  • Training jobs & status                                 │  │
│  │  • Model versions & metadata                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         File Storage (S3/MinIO/Local FS)                  │  │
│  │  • 3D assembly files (.blend, .obj, .stl, .fbx)          │  │
│  │  • Generated synthetic datasets                           │  │
│  │  • Trained model files (.pt, .tflite, .mlpackage)        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Multi-Platform Deployment Strategy

### Platform Priorities

The system supports multiple device types for flexible deployment:

**Phase 1 (Current):** iOS Native App
- ✅ Swift implementation complete (`yolo-ios-app/`)
- ✅ Core ML model inference optimized for Neural Engine
- ✅ Real-time camera detection with AVFoundation
- **Status:** Production-ready

**Phase 2 (Next):** Android Mobile App
- 🚧 Flutter or native Kotlin implementation
- 🚧 TensorFlow Lite model integration
- 🚧 Camera2 API for camera access
- **Timeline:** 6-8 weeks development
- **Recommendation:** Start with Flutter for faster development

**Phase 3 (Future):** Windows PC with Webcam
- 💡 Desktop application (Electron/PyQt/Web)
- 💡 ONNX Runtime or PyTorch inference
- 💡 DirectShow/OpenCV for webcam access
- **Timeline:** 4-6 weeks development
- **Use Cases:** Fixed workstation inspection, high-resolution cameras

**Phase 4 (Advanced):** Zed2i Stereo Camera Integration
- 💡 ZED SDK integration for depth sensing
- 💡 3D bounding boxes with spatial coordinates
- 💡 Dimensional measurements (distance, volume)
- 💡 Occlusion handling via depth maps
- **Timeline:** 8-12 weeks development (requires specialized hardware)
- **Use Cases:** Robotic guidance, precision QA, autonomous systems

### Implementation Roadmap: Multi-Platform Support

#### Android App Development (6-8 weeks)
1. **Week 1-2:** Flutter project setup + UI design
2. **Week 3-4:** TFLite model integration + camera pipeline
3. **Week 5-6:** Real-time inference + bounding box overlay
4. **Week 7-8:** Testing + Play Store deployment

#### Windows Desktop App (4-6 weeks)
1. **Week 1-2:** Technology selection (Electron vs PyQt vs Web)
2. **Week 3-4:** ONNX model integration + webcam access
3. **Week 5-6:** UI development + performance optimization

#### Zed2i Camera Integration (8-12 weeks)
1. **Week 1-3:** ZED SDK learning + depth data exploration
2. **Week 4-6:** 3D detection algorithm development
3. **Week 7-9:** Spatial measurement features
4. **Week 10-12:** Robotic API integration + testing

---

## 📅 Development Phases

### **Phase 1: Foundation & Backend Infrastructure** (Weeks 1-4)

#### Milestone 1.1: Backend Server Setup
- [ ] Set up FastAPI/Flask project structure
- [ ] Implement PostgreSQL database schema
- [ ] User authentication system (JWT tokens)
- [ ] Basic REST API endpoints (health, auth)
- [ ] Docker containerization for server
- [ ] Environment configuration management

#### Milestone 1.2: File Upload & Storage
- [ ] Design file storage architecture (S3/MinIO/Local)
- [ ] Implement multi-format 3D file upload (Blender, OBJ, STL, FBX)
- [ ] File validation and sanitization
- [ ] Assembly project CRUD operations
- [ ] User file quota management

#### Milestone 1.3: Job Queue System
- [ ] Set up Celery with Redis/RabbitMQ
- [ ] Design job state machine (Pending → Processing → Complete/Failed)
- [ ] Implement progress tracking & logging
- [ ] Worker health monitoring
- [ ] Job cancellation mechanism

**Deliverable:** Backend server accepting file uploads, managing users, and queuing jobs

---

### **Phase 2: Blender Automation Pipeline** (Weeks 5-8)

#### Milestone 2.1: Blender Scene Generation
- [ ] Adapt existing `eevee_desk_scene17_dualpass.py` for dynamic scenes
- [ ] 3D file import automation (OBJ, STL, FBX → Blender)
- [ ] Automatic scene setup (camera, lighting, materials)
- [ ] Object-to-class mapping configuration
- [ ] Randomization parameters (camera angles, lighting, backgrounds)

#### Milestone 2.2: Synthetic Data Generation
- [ ] Celery worker for Blender rendering tasks
- [ ] Memory-optimized batch rendering
- [ ] YOLO label format generation
- [ ] Dataset validation & quality checks
- [ ] Progress reporting to API (% complete)

#### Milestone 2.3: Scene Configuration UI/API
- [ ] API endpoints for render parameters (num_images, resolution, samples)
- [ ] Class/object mapping configuration
- [ ] Background image upload (optional)
- [ ] Preview image generation (1-2 samples before full render)

**Deliverable:** Automated Blender pipeline generating synthetic datasets from uploaded 3D files

---

### **Phase 3: Model Training Pipeline** (Weeks 9-12)

#### Milestone 3.1: YOLO Training Integration
- [ ] Ultralytics YOLO integration (YOLOv8/YOLOv11)
- [ ] Automatic dataset.yaml generation
- [ ] Training job Celery worker
- [ ] Hyperparameter configuration API
- [ ] GPU resource management (queue if busy)

#### Milestone 3.2: Training Monitoring
- [ ] Real-time training metrics (mAP, loss, precision/recall)
- [ ] TensorBoard integration
- [ ] Training logs streaming via WebSocket/SSE
- [ ] Early stopping on convergence
- [ ] Model checkpoint management

#### Milestone 3.3: Model Conversion & Optimization
- [ ] PyTorch (.pt) → TensorFlow Lite (.tflite) conversion
- [ ] PyTorch (.pt) → Core ML (.mlpackage) conversion
- [ ] Model quantization (FP16/INT8) for mobile
- [ ] Model size validation (<50MB target)
- [ ] Accuracy benchmarking post-conversion

**Deliverable:** Automated training pipeline producing mobile-optimized models

---

### **Phase 4: Flutter Mobile App Development** (Weeks 13-20)

#### Milestone 4.1: Flutter Project Setup
- [ ] Create Flutter project structure
- [ ] State management setup (Riverpod/Bloc/Provider)
- [ ] API client with Dio/http
- [ ] Authentication flow (login, signup, JWT storage)
- [ ] Theming and UI foundations

#### Milestone 4.2: Assembly Upload Flow
- [ ] File picker integration (3D file selection)
- [ ] Multi-file upload with progress bars
- [ ] Assembly project creation UI
- [ ] Class/object labeling interface
- [ ] Render configuration form (simple/advanced modes)

#### Milestone 4.3: Training Job Management
- [ ] Job list view (pending, processing, complete)
- [ ] Real-time progress updates (WebSocket/SSE)
- [ ] Training metrics visualization (charts)
- [ ] Job history & logs viewer
- [ ] Push notifications for job completion

#### Milestone 4.4: Camera Inference
- [ ] Camera plugin integration (camera package)
- [ ] TensorFlow Lite model loading
- [ ] Real-time inference pipeline (frame → model → overlay)
- [ ] Bounding box/segmentation mask rendering
- [ ] FPS and performance metrics display

#### Milestone 4.5: Model Management
- [ ] Model download from server
- [ ] Local model versioning
- [ ] Model switching UI (test multiple models)
- [ ] Model performance comparison
- [ ] Auto-update models on new training completion

**Deliverable:** Fully functional Flutter app with upload, training, and inference

---

### **Phase 5: Connectivity & Deployment** (Weeks 21-24)

#### Milestone 5.1: Multiple Connectivity Options
- [ ] **Option A: Direct IP Connection**
  - Server advertises on local network (mDNS/Bonjour)
  - Manual IP/port configuration
  - Connection health checks

- [ ] **Option B: ngrok Integration**
  - Automatic ngrok tunnel creation
  - Dynamic URL updates to app
  - HTTPS certificate handling

- [ ] **Option C: VPN (Netbird/Tailscale)**
  - VPN setup documentation
  - Private IP configuration
  - Connection reliability testing

#### Milestone 5.2: Server Deployment Options
- [ ] Local PC server setup guide (Windows/macOS/Linux)
- [ ] Docker Compose full-stack deployment
- [ ] Cloud deployment (AWS/GCP/Azure) documentation
- [ ] Kubernetes manifests (optional, for scale)
- [ ] Backup and disaster recovery procedures

#### Milestone 5.3: Performance & Optimization
- [ ] Model caching strategies
- [ ] Dataset compression for storage
- [ ] API rate limiting & quotas
- [ ] Monitoring & alerting (Prometheus/Grafana)
- [ ] Cost optimization for cloud hosting

**Deliverable:** Production-ready deployment with multiple connectivity options

---

### **Phase 6: Advanced Features & Polish** (Weeks 25-30)

#### Milestone 6.1: Enhanced UX
- [ ] Onboarding tutorial for new users
- [ ] Sample assembly projects (pre-loaded)
- [ ] Model accuracy suggestions (increase dataset size, adjust params)
- [ ] Dark mode support
- [ ] Internationalization (i18n) for multiple languages

#### Milestone 6.2: Collaboration Features
- [ ] Share assembly projects between users
- [ ] Public model marketplace (browse/download models)
- [ ] Model ratings & reviews
- [ ] Community-contributed backgrounds/textures

#### Milestone 6.3: Advanced Training
- [ ] Transfer learning from existing models
- [ ] Custom augmentation strategies
- [ ] Multi-class object detection
- [ ] Instance segmentation support
- [ ] Active learning (flag hard examples for re-training)

#### Milestone 6.4: Analytics & Insights
- [ ] Usage analytics dashboard (admin)
- [ ] Model performance analytics (per-user)
- [ ] Resource utilization tracking (GPU hours, storage)
- [ ] User feedback collection system

**Deliverable:** Feature-complete SaaS platform ready for beta launch

---

## 🛠️ Technical Stack Recommendations

### Backend
- **Framework:** FastAPI (modern, async, auto-docs) or Flask (simpler, mature)
- **Database:** PostgreSQL (relational, robust) or MongoDB (flexible schema)
- **Job Queue:** Celery + Redis (industry standard)
- **Storage:** MinIO (self-hosted S3 alternative) or AWS S3
- **Cache:** Redis (for sessions, job status)

### Mobile App
- **Framework:** Flutter 3.x (cross-platform iOS + Android)
- **State Management:** Riverpod (modern) or Bloc (structured)
- **HTTP Client:** Dio (feature-rich) or http (official)
- **ML Framework:** TensorFlow Lite (cross-platform inference)
- **Camera:** camera package or flutter_vision for YOLO

### ML Pipeline
- **Training:** Ultralytics YOLOv8/v11 (easiest API)
- **Conversion:** coremltools (Core ML), tf2onnx + onnx2tflite (TFLite)
- **Rendering:** Blender 4.5+ with Python API

### DevOps
- **Containerization:** Docker + Docker Compose
- **Orchestration:** Kubernetes (optional, for scale)
- **CI/CD:** GitHub Actions or GitLab CI
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana) or Loki

---

## 🚧 Technical Challenges & Solutions

### Challenge 1: Long Training Times
**Problem:** Training can take 30min - 2hrs, blocking users
**Solutions:**
- Async job queue with progress tracking
- Email/push notifications on completion
- Priority queue for premium users
- Distributed training across multiple GPUs

### Challenge 2: Large Model Files
**Problem:** 50-200MB models slow to download
**Solutions:**
- Model compression (quantization, pruning)
- Incremental model updates (delta patches)
- CDN distribution for models
- On-device model caching

### Challenge 3: 3D File Format Compatibility
**Problem:** Users have varied file formats (Blender, CAD, mesh)
**Solutions:**
- Support multiple formats (OBJ, STL, FBX, GLTF)
- Assimp library for format conversion
- Validation and preview before processing
- Clear format requirements documentation

### Challenge 4: GPU Resource Contention
**Problem:** Multiple users requesting training simultaneously
**Solutions:**
- Job queue with fair scheduling
- GPU time quotas per user
- Spot instance auto-scaling (cloud)
- Training progress transparency

### Challenge 5: Network Connectivity
**Problem:** Mobile app needs reliable server connection
**Solutions:**
- Multiple connectivity options (IP, ngrok, VPN)
- Automatic reconnection logic
- Offline mode for inference with cached models
- Connection status UI indicators

### Challenge 6: Real-Time Inference Performance
**Problem:** 30 FPS inference on mobile devices
**Solutions:**
- Model quantization (INT8)
- Use mobile-optimized architectures (YOLOv8n)
- GPU acceleration (Metal on iOS, OpenGL on Android)
- Resolution downscaling (640x640 instead of 1280x1280)

---

## 📊 Success Metrics

### Phase 1-3 (Backend & ML Pipeline)
- [ ] User can upload 3D file and receive synthetic dataset in <10 mins
- [ ] Model training completes in <30 mins for 500 images
- [ ] Model conversion success rate >95%
- [ ] API response time <200ms (p95)

### Phase 4-5 (Mobile App & Deployment)
- [ ] App achieves >20 FPS inference on mid-range phones
- [ ] Model download <2 mins on 4G connection
- [ ] Zero-config setup for ngrok option
- [ ] <5 min setup time for local server deployment

### Phase 6 (Advanced Features)
- [ ] User retention >60% after first model training
- [ ] Average 3+ assembly projects per active user
- [ ] Model marketplace has >50 community models
- [ ] Platform uptime >99.5%

---

## 🎓 Learning Resources for Team

### Flutter Development
- Official Flutter Docs: https://flutter.dev/docs
- TensorFlow Lite in Flutter: https://pub.dev/packages/tflite_flutter
- Camera handling: https://pub.dev/packages/camera

### FastAPI & Backend
- FastAPI Docs: https://fastapi.tiangolo.com
- Celery Best Practices: https://docs.celeryproject.org
- Docker Compose: https://docs.docker.com/compose

### YOLO & ML
- Ultralytics Docs: https://docs.ultralytics.com
- Core ML Tools: https://coremltools.readme.io
- TFLite Converter: https://www.tensorflow.org/lite/convert

### Blender Python API
- Blender Python API: https://docs.blender.org/api/current
- Scripting Blender: https://docs.blender.org/manual/en/latest/advanced/scripting

---

## 🚀 MVP Definition (Minimum Viable Product)

To validate the concept quickly, the MVP should include:

### MVP Scope (8-10 weeks)
1. **Backend:**
   - User authentication
   - Single 3D file upload (Blender .blend only)
   - Hardcoded render parameters (300 images, 640x640)
   - YOLO training with default hyperparameters
   - TFLite model conversion

2. **Mobile App:**
   - Login/signup
   - Upload single assembly file
   - "Start Training" button (one-click)
   - Job progress bar
   - Download trained model
   - Camera inference with bounding boxes

3. **Connectivity:**
   - ngrok only (simplest setup)

### Post-MVP Additions
- Multiple file formats
- Custom render parameters
- Core ML support (iOS)
- Direct IP / VPN options
- Model management UI
- Advanced training options

---

## 💰 Cost Estimates (Self-Hosted on PC)

### Hardware Requirements
- **GPU:** RTX 3060+ (12GB VRAM minimum) - $300-500
- **RAM:** 32GB+ - $100-150
- **Storage:** 1TB NVMe SSD - $80-120
- **Total:** ~$500-800 initial investment

### Operating Costs
- **Electricity:** ~$20-40/month (24/7 server)
- **ngrok Pro:** $8/month (custom domain, no limits)
- **Backup Storage:** $5-10/month (cloud backup)
- **Total:** ~$35-60/month

### Cloud Alternative (AWS/GCP)
- **Compute:** g4dn.xlarge (GPU instance) ~$0.50/hr = $360/month (24/7)
- **Storage:** S3 100GB ~$3/month
- **Database:** RDS small instance ~$30/month
- **Total:** ~$400-500/month
- **Recommendation:** Use spot instances + auto-scaling to reduce to ~$150-200/month

---

## 🎯 Next Steps

1. **Review this roadmap** and prioritize phases
2. **Choose MVP scope** vs full feature set
3. **Decide on tech stack** (FastAPI vs Flask, etc.)
4. **Set up development environment** (Python, Flutter, Docker)
5. **Create detailed TODO.md** with week-by-week tasks
6. **Start Phase 1 implementation** (backend foundation)

---

## 📝 Notes & Considerations

### Scalability
- Designed for 10-100 concurrent users initially
- Horizontal scaling possible via Kubernetes
- Database sharding for 1000+ users

### Security
- All API calls require JWT authentication
- File upload size limits (500MB max)
- Rate limiting on expensive operations
- Input validation for 3D files (prevent malicious uploads)

### Maintenance
- Regular model format updates (new YOLO versions)
- Blender API changes (quarterly updates)
- Mobile OS updates (Flutter framework upgrades)
- Security patches for dependencies

### Legal & Privacy
- User data ownership policies
- Model licensing (user-generated models)
- GDPR compliance (if EU users)
- Terms of service for platform usage

---

**Last Updated:** 2025-12-03
**Version:** 1.0
**Status:** Planning Phase
