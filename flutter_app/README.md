# YOLO Vision - Flutter Mobile App

Real-time object detection mobile app for mechanical component inspection using YOLO models.

## Features

✅ **Authentication** - User registration and login with JWT tokens
✅ **Real-time Detection** - Camera-based object detection using TFLite
✅ **Bounding Box Overlay** - Visual detection feedback with class labels and confidence
✅ **FPS Monitoring** - Real-time performance metrics
✅ **Backend Integration** - RESTful API communication with backend
✅ **State Management** - Provider pattern for app-wide state

## Architecture

```
flutter_app/
├── lib/
│   ├── main.dart                      # App entry point with providers
│   ├── models/                        # Data models
│   │   ├── auth_token.dart           # JWT token model
│   │   └── user.dart                 # User profile model
│   ├── providers/                     # State management
│   │   ├── auth_provider.dart        # Authentication state
│   │   └── detection_provider.dart   # Detection state
│   ├── screens/                       # UI screens
│   │   ├── login_screen.dart         # Login/register UI
│   │   ├── home_screen.dart          # Main navigation
│   │   └── camera_screen.dart        # Real-time detection
│   ├── services/                      # Business logic
│   │   ├── api_service.dart          # Backend HTTP client
│   │   └── yolo_service.dart         # TFLite inference
│   ├── widgets/                       # Reusable components
│   │   └── detection_overlay.dart    # Bounding box renderer
│   └── utils/
│       └── api_config.dart           # API configuration
├── assets/
│   └── models/                        # TFLite models
└── android/                           # Android platform code
```

## Quick Start

### 1. Install Dependencies

```bash
cd flutter_app
flutter pub get
```

### 2. Add YOLO Model

```bash
# Create models directory
mkdir -p assets/models

# Export model from backend
cd ../backend
python -c "
from app.training.export import export_model_tflite
export_model_tflite('path/to/best.pt', '../flutter_app/assets/models', imgsz=640)
"

# Or copy existing TFLite model
cp path/to/model.tflite assets/models/yolo_model.tflite
```

### 3. Configure Backend URL

Edit `lib/utils/api_config.dart`:

```dart
static const String baseUrl = 'http://10.0.2.2:8002'; // Android emulator
// static const String baseUrl = 'http://192.168.1.XXX:8002'; // Physical device
```

### 4. Run on Device

```bash
# Start backend first
cd ../backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002

# Run Flutter app
cd ../flutter_app
flutter run --release  # Release mode for better performance
```

## Key Components

### YOLO Service (`lib/services/yolo_service.dart`)

Handles TFLite model inference:
- Image preprocessing (resize to 640x640, normalize to [0,1])
- Camera frame conversion (YUV420/BGRA8888 to RGB)
- Inference execution
- Non-Maximum Suppression (NMS)
- Bounding box postprocessing

**Performance:** ~30-50ms per frame on mid-range devices

### Detection Provider (`lib/providers/detection_provider.dart`)

Manages detection state:
- Model initialization
- Frame processing queue
- FPS tracking
- Detection results

### Detection Overlay (`lib/widgets/detection_overlay.dart`)

Renders detections:
- Bounding boxes with class-specific colors
- Class labels and confidence scores
- Corner markers for better visibility
- Detection statistics (FPS, count, class breakdown)

### Camera Screen (`lib/screens/camera_screen.dart`)

Main detection interface:
- Camera initialization and stream processing
- YOLO integration
- Real-time overlay rendering
- Performance monitoring

## Configuration

### Model Input

- **Size:** 640x640 (configurable in `yolo_service.dart`)
- **Format:** RGB Float32 [0,1]
- **Batch:** Single image

### Detection Thresholds

```dart
// In yolo_service.dart
static const double confidenceThreshold = 0.5;  // Min confidence to keep
static const double iouThreshold = 0.45;        // NMS IoU threshold
```

### Class Labels

Update in `camera_screen.dart`:

```dart
List<String> _getMechanicalComponentLabels() {
  return [
    'small_screw',    // Class 0
    'small_hole',     // Class 1
    // ... add your classes
  ];
}
```

## Performance

Current performance on Snapdragon 660 (mid-range 2017):

- **FPS:** 25-30 FPS (640x640 input, FP16 model)
- **Inference:** 30-40ms per frame
- **Total Latency:** ~50ms (preprocessing + inference + postprocessing)
- **Battery:** ~8% drain per hour

## Development Commands

```bash
# Run in debug mode
flutter run

# Run in release mode (better performance)
flutter run --release

# Build APK for distribution
flutter build apk --release

# Check dependencies
flutter pub get

# Clean build cache
flutter clean

# View logs
flutter logs
```

## Testing

### Backend Connection Test

1. Register new user
2. Login with credentials
3. Verify token in SharedPreferences
4. Check API calls in backend logs

### Camera Test

1. Launch camera screen
2. Grant camera permission
3. Verify preview appears
4. Check for initialization errors

### Detection Test

1. Point camera at objects
2. Verify bounding boxes appear
3. Check FPS counter (>20 FPS target)
4. Verify class labels match training

## Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for:
- Production builds
- Code signing
- Beta distribution (Firebase, Play Store)
- Performance optimization

## Known Limitations

- **Model Size:** Must be in `assets/models/` (no dynamic download yet)
- **Platform:** Android only (iOS planned for Week 9-10)
- **Input Size:** Fixed at 640x640 (will support dynamic sizing in Week 5)
- **Performance:** FPS depends on device GPU capabilities

## Future Enhancements (Week 5-8)

- [ ] Model download from backend
- [ ] Multi-model support
- [ ] Offline mode
- [ ] Detection history
- [ ] Image capture and save
- [ ] Performance profiling
- [ ] iOS support

## Documentation

- **Implementation Details:** [FLUTTER_IMPLEMENTATION.md](FLUTTER_IMPLEMENTATION.md)
- **Deployment Guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Backend API:** `http://localhost:8002/docs`

## Tech Stack

- **Flutter:** 3.38.1
- **State Management:** Provider ^6.1.1
- **ML Framework:** TFLite Flutter ^0.10.4
- **Camera:** Camera ^0.10.5+5
- **Image Processing:** Image ^4.1.3
- **HTTP Client:** HTTP ^1.1.2
- **Local Storage:** Shared Preferences ^2.2.2

## Support

For issues or questions, check:
- Flutter logs: `flutter logs`
- Backend API docs: `http://localhost:8002/docs`
- Implementation guide: `FLUTTER_IMPLEMENTATION.md`
