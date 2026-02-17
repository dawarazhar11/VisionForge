# Multi-Platform Requirements & Implementation Guide

**Last Updated:** 2025-12-04
**Status:** Planning & Partial Implementation

---

## 🎯 Platform Support Overview

This document defines the requirements and implementation approach for supporting YOLO computer vision inference across multiple device types:

1. **iOS (Native Swift)** - ✅ Implemented
2. **Android (Mobile)** - 🚧 Planned
3. **Windows PC (Webcam)** - 💡 Future
4. **Zed2i Stereo Camera** - 💡 Advanced Feature

---

## 📱 Platform 1: iOS (Native Swift)

### Status: ✅ Production Ready

**Implementation Location:** `yolo-ios-app/`

### Key Features
- Real-time object detection using Core ML
- Optimized for Apple Neural Engine (A12 Bionic+)
- Camera integration via AVFoundation
- Minimum iOS 16.0 support
- Swift Package Manager for dependencies

### Model Requirements
- **Format:** Core ML (.mlpackage)
- **Input Size:** 640x640 (configurable)
- **Export Command:**
  ```python
  from ultralytics import YOLO
  model = YOLO('best.pt')
  model.export(format='coreml', nms=True, imgsz=640)
  ```

### Performance Targets
- **Inference Speed:** >30 FPS on iPhone 12+
- **Model Size:** <50MB
- **Battery Impact:** <5% per 10 minutes of continuous detection

### Deployment
- **Distribution:** App Store or TestFlight
- **Requirements:** Apple Developer account ($99/year)
- **Code Signing:** Automatic via Xcode

---

## 🤖 Platform 2: Android (Mobile)

### Status: 🚧 Planned - Next Priority

### Implementation Options

#### Option A: Flutter App (Recommended)
**Pros:**
- Faster development (6-8 weeks vs 10-12 for native)
- Cross-platform codebase (can share with future iOS Flutter port)
- Excellent TFLite integration via `tflite_flutter` package
- Hot reload for rapid iteration

**Cons:**
- Larger app size (~25MB base vs ~10MB native)
- Slight performance overhead compared to native Kotlin

**Tech Stack:**
```yaml
flutter: ^3.16.0
camera: ^0.10.5
tflite_flutter: ^0.10.4
provider: ^6.1.1  # or riverpod for state management
```

#### Option B: Native Kotlin App (Alternative)
**Pros:**
- Maximum performance
- Smaller app size
- Direct Android API access

**Cons:**
- Longer development time (10-12 weeks)
- Separate codebase from iOS
- More maintenance overhead

### Model Requirements
- **Format:** TensorFlow Lite (.tflite)
- **Quantization:** FP16 (balance of speed/accuracy)
- **Export Command:**
  ```python
  from ultralytics import YOLO
  model = YOLO('best.pt')
  model.export(format='tflite', int8=False, imgsz=640)
  ```

### Performance Targets
- **Inference Speed:** >20 FPS on mid-range devices (Snapdragon 7-series)
- **Model Size:** <30MB
- **Battery Impact:** <8% per 10 minutes of continuous detection

### Hardware Requirements
- **Minimum:** Android 8.0 (API 26)
- **Recommended:** Android 11+ for Neural Networks API acceleration
- **GPU:** OpenGL ES 3.0+ for GPU delegates

### Development Timeline (Flutter)
1. **Week 1-2:** Project setup, UI design, backend API integration
2. **Week 3-4:** TFLite model loading, camera pipeline setup
3. **Week 5-6:** Real-time inference, bounding box overlay, performance optimization
4. **Week 7-8:** Testing (devices, Android versions), Play Store deployment

---

## 🖥️ Platform 3: Windows PC with Webcam

### Status: 💡 Future Feature

### Use Cases
- Fixed workstation inspection setups
- Desktop-based quality control stations
- High-resolution webcam support (4K)
- Multi-monitor workflows (camera + results display)
- Offline factory floor deployments

### Implementation Options

#### Option A: Electron Desktop App
**Pros:**
- Cross-platform (Windows/Mac/Linux)
- Web technologies (TypeScript/React)
- Easy UI development

**Cons:**
- Large app size (~150MB)
- Higher memory usage

**Tech Stack:**
```json
{
  "electron": "^28.0.0",
  "onnxruntime-web": "^1.17.0",
  "opencv.js": "^4.9.0",
  "react": "^18.2.0"
}
```

#### Option B: PyQt Desktop App
**Pros:**
- Native Python integration
- Direct access to PyTorch models (no conversion needed)
- Smaller app size (~80MB)

**Cons:**
- Python runtime required (or bundled with PyInstaller)
- UI development more complex than web

**Tech Stack:**
```python
PyQt6 >= 6.6.0
torch >= 2.1.0
opencv-python >= 4.9.0
onnxruntime >= 1.17.0  # For optimized inference
```

#### Option C: Web Application (Browser-Based)
**Pros:**
- No installation required
- Cross-platform by default
- Easy updates (server-side)

**Cons:**
- Requires network connection to backend
- Camera access via WebRTC (browser security constraints)

**Tech Stack:**
```javascript
// Frontend
React + TypeScript
ONNX.js for browser inference

// Backend (if needed)
FastAPI for serving models
WebRTC for camera streaming
```

### Model Requirements
- **Format:** ONNX (.onnx) or PyTorch (.pt)
- **Export Command:**
  ```python
  from ultralytics import YOLO
  model = YOLO('best.pt')
  model.export(format='onnx', imgsz=640, opset=12)
  ```

### Performance Targets
- **Inference Speed:** >40 FPS on modern desktop GPU (GTX 1060+)
- **CPU Fallback:** >15 FPS on recent Intel/AMD CPUs
- **Model Size:** <100MB

### Hardware Requirements
- **OS:** Windows 10/11 (64-bit)
- **RAM:** 8GB minimum, 16GB recommended
- **GPU:** Optional but recommended (NVIDIA/AMD with OpenCL support)
- **Webcam:** USB 2.0+ (720p minimum, 1080p/4K supported)

### Development Timeline
1. **Week 1-2:** Technology selection, prototype development
2. **Week 3-4:** Model integration, webcam access, performance testing
3. **Week 5-6:** UI polish, installer creation, documentation

---

## 📷 Platform 4: Zed2i Stereo Camera Integration

### Status: 💡 Advanced Feature - Long-Term Roadmap

### Hardware: Stereolabs ZED 2i
- **Cost:** ~$450 USD
- **Resolution:** 2.2MP per sensor (dual cameras)
- **Depth Range:** 0.3m - 20m
- **Frame Rate:** Up to 120 FPS (configurable)
- **SDK:** ZED SDK 4.0+ (C++, Python, Unity, ROS)

### Advanced Capabilities

#### 1. 3D Object Detection
- Convert 2D bounding boxes to 3D bounding boxes using depth data
- Output format: `[x, y, z, width, height, depth]` in world coordinates
- Enables spatial reasoning (object in front/behind/beside)

#### 2. Dimensional Measurements
**Use Cases:**
- Measure screw spacing (e.g., "12.5mm apart")
- Verify bracket alignment (e.g., "3mm offset from center")
- Quality control (e.g., "component is 2mm shorter than spec")

**Implementation:**
```python
# Pseudocode
detection = yolo_model.predict(frame)
for bbox in detection.boxes:
    # Get depth at bbox center
    depth = zed_depth_map[bbox.center_y, bbox.center_x]

    # Convert pixel dimensions to real-world mm
    real_width_mm = pixel_to_mm(bbox.width, depth, camera_intrinsics)
    real_height_mm = pixel_to_mm(bbox.height, depth, camera_intrinsics)
```

#### 3. Occlusion Handling
- Use depth discontinuities to detect occlusions
- Improve detection accuracy in cluttered scenes
- Separate foreground objects from background

#### 4. Robotic Integration
**Applications:**
- Robotic pick-and-place guidance (provide 3D coordinates to robot arm)
- Autonomous inspection systems (navigate around detected components)
- Safety distance monitoring (alert if human enters robot workspace)

**ROS Integration:**
```bash
# Publish detections with 3D coordinates
/yolo/detections_3d  # geometry_msgs/PoseArray
/yolo/depth_map      # sensor_msgs/Image
/yolo/point_cloud    # sensor_msgs/PointCloud2
```

### Model Requirements
- **Same as 2D Detection:** YOLO models remain unchanged
- **Additional Processing:** Depth fusion happens post-detection
- **Format:** PyTorch (.pt) or ONNX (.onnx) - need full Python environment

### Performance Targets
- **3D Detection:** >20 FPS (includes depth processing overhead)
- **Measurement Accuracy:** ±1mm at <1m distance, ±5mm at 5m
- **Latency:** <100ms total (detection + depth fusion)

### Hardware Requirements
- **Zed2i Camera:** $450 (one-time cost)
- **GPU:** NVIDIA GTX 1060 or better (required for ZED SDK)
- **USB:** USB 3.0 Type-C
- **OS:** Ubuntu 20.04/22.04 or Windows 10/11
- **CUDA:** 11.x or 12.x

### Software Stack
```python
# Core dependencies
zed-python >= 4.0.0
ultralytics >= 8.0.0
numpy >= 1.24.0
open3d >= 0.18.0  # For point cloud visualization

# Optional - ROS integration
ros-noetic-desktop-full  # ROS 1
# or
ros-humble-desktop  # ROS 2
```

### Development Timeline (Estimated)
1. **Week 1-3:** ZED SDK learning, depth map exploration, camera calibration
2. **Week 4-6:** 2D-to-3D projection algorithm, coordinate system transforms
3. **Week 7-9:** Dimensional measurement features, accuracy validation
4. **Week 10-12:** Robotic API integration (ROS/REST), testing in real scenarios

### Recommended Development Phases
**Phase 1 (MVP):** 3D bounding boxes only
**Phase 2:** Dimensional measurements
**Phase 3:** Occlusion handling
**Phase 4:** Full robotic integration

---

## 🔄 Multi-Platform Model Export Workflow

To support all platforms, the training backend must export models in all required formats:

### Complete Export Script
```python
from ultralytics import YOLO
import os

def export_all_formats(trained_model_path: str, output_dir: str):
    """
    Export trained YOLO model to all supported formats.

    Args:
        trained_model_path: Path to best.pt file from training
        output_dir: Directory to save exported models
    """
    model = YOLO(trained_model_path)

    # iOS - Core ML
    print("Exporting to Core ML for iOS...")
    coreml_path = model.export(
        format='coreml',
        nms=True,
        imgsz=640,
        half=True  # FP16 for smaller size
    )
    print(f"✓ Core ML: {coreml_path}")

    # Android - TensorFlow Lite
    print("Exporting to TFLite for Android...")
    tflite_path = model.export(
        format='tflite',
        int8=False,  # Use FP16 quantization
        imgsz=640
    )
    print(f"✓ TFLite: {tflite_path}")

    # Windows/Zed2i - ONNX
    print("Exporting to ONNX for Windows/Zed2i...")
    onnx_path = model.export(
        format='onnx',
        imgsz=640,
        opset=12,  # Compatible with most ONNX runtimes
        dynamic=False  # Fixed input size for faster inference
    )
    print(f"✓ ONNX: {onnx_path}")

    # Original PyTorch (for Python-based systems)
    print(f"✓ PyTorch: {trained_model_path}")

    return {
        'coreml': coreml_path,
        'tflite': tflite_path,
        'onnx': onnx_path,
        'pytorch': trained_model_path
    }

# Usage in training pipeline
if __name__ == "__main__":
    exported = export_all_formats(
        'runs/train/exp/weights/best.pt',
        'exported_models/'
    )
    print("\nAll exports completed:")
    for platform, path in exported.items():
        print(f"  {platform}: {path}")
```

### File Size Expectations
| Format | Typical Size | Notes |
|--------|-------------|-------|
| PyTorch (.pt) | 6-50 MB | Base model, unoptimized |
| Core ML (.mlpackage) | 4-40 MB | Apple-optimized, usually smaller |
| TFLite (.tflite) | 5-30 MB | With FP16 quantization |
| ONNX (.onnx) | 6-50 MB | Similar to PyTorch |

---

## 🧪 Testing Requirements

### Per-Platform Testing Matrix

| Test Case | iOS | Android | Windows | Zed2i |
|-----------|-----|---------|---------|-------|
| Model loading | ✅ | 🚧 | 💡 | 💡 |
| Camera access | ✅ | 🚧 | 💡 | 💡 |
| Real-time inference (>20 FPS) | ✅ | 🚧 | 💡 | 💡 |
| Bounding box overlay | ✅ | 🚧 | 💡 | 💡 |
| Multi-object detection | ✅ | 🚧 | 💡 | 💡 |
| Low-light conditions | ✅ | 🚧 | 💡 | 💡 |
| Model update mechanism | ✅ | 🚧 | 💡 | 💡 |
| 3D coordinate output | N/A | N/A | N/A | 💡 |
| Dimensional measurements | N/A | N/A | N/A | 💡 |

Legend: ✅ Tested | 🚧 In Progress | 💡 Planned | N/A Not Applicable

### Device Coverage

**iOS Testing:**
- iPhone 12 (A14 Bionic)
- iPhone 13 Pro (A15 Bionic)
- iPad Air 5th Gen (M1)

**Android Testing (Planned):**
- Samsung Galaxy S21 (Snapdragon 888)
- Google Pixel 6 (Tensor)
- Xiaomi Redmi Note 11 (Snapdragon 680 - budget device)

**Windows Testing (Planned):**
- Desktop: i7-10700K + RTX 3060
- Laptop: i5-1240P (integrated graphics only)

**Zed2i Testing (Planned):**
- Ubuntu 22.04 + RTX 3070
- Windows 11 + RTX 3060

---

## 📋 Priority Roadmap

### Q1 2025: Android Launch
- Complete Flutter Android app development
- TFLite model integration
- Play Store deployment
- Cross-platform testing

### Q2 2025: Windows Desktop
- Technology selection (Electron vs PyQt)
- Prototype development
- Webcam integration
- Installer creation

### Q3-Q4 2025: Zed2i Integration
- Hardware procurement
- ZED SDK integration
- 3D detection algorithm
- Robotic API development

---

## 💰 Cost Analysis

### Development Costs (Estimated)

| Platform | Developer Time | External Costs | Total Cost |
|----------|---------------|----------------|------------|
| iOS (Swift) | ✅ Complete | $99/year (Apple Dev) | $99/year |
| Android (Flutter) | 6-8 weeks | $25 (Google Play) | ~$9,000 + $25 |
| Windows Desktop | 4-6 weeks | $0 (open source) | ~$6,000 |
| Zed2i Integration | 8-12 weeks | $450 (camera) | ~$15,000 + $450 |

**Assumptions:** Developer hourly rate = $75/hour, full-time work

### Hardware Costs (Per Deployment)

| Platform | Hardware Cost | Notes |
|----------|--------------|-------|
| iOS | $500-1200 | iPhone 12+ or iPad |
| Android | $150-800 | Wide range of devices |
| Windows PC | $800-1500 | Desktop with webcam |
| Zed2i System | $2000-3000 | PC + Zed2i + GPU |

---

## 📚 Additional Resources

### iOS Development
- Swift Package: `yolo-ios-app/Sources/YOLO/`
- Core ML Guide: `update_ios_model.md`
- Apple Developer: https://developer.apple.com/coreml/

### Android Resources
- Flutter: https://flutter.dev
- TFLite Plugin: https://pub.dev/packages/tflite_flutter
- Android Studio: https://developer.android.com/studio

### Windows Development
- Electron: https://www.electronjs.org
- PyQt: https://www.riverbankcomputing.com/software/pyqt/
- ONNX Runtime: https://onnxruntime.ai

### Zed2i Resources
- ZED SDK: https://www.stereolabs.com/developers
- Hardware: https://www.stereolabs.com/zed-2i/
- ROS Integration: https://github.com/stereolabs/zed-ros-wrapper

---

**Next Steps:**
1. Review this document with stakeholders
2. Prioritize platform development order
3. Allocate resources and timeline
4. Begin Android development (recommended next priority)

**Document Maintainer:** Update this file as platforms are implemented and requirements evolve.
