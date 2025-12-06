# Flutter App Deployment Guide

This guide covers deploying the YOLO Vision Flutter app for Android beta testing.

## Prerequisites

- Flutter SDK 3.38.1 or higher
- Android Studio with Android SDK
- Android device or emulator (API 21+)
- Trained YOLO model exported to TFLite format

## Quick Start

### 1. Install Dependencies

```bash
cd flutter_app
flutter pub get
```

### 2. Add Your YOLO Model

Place your trained TFLite model in the assets folder:

```bash
# Create models directory if it doesn't exist
mkdir -p assets/models

# Copy your trained model
# Example: cp path/to/your/model.tflite assets/models/yolo_model.tflite
```

**Important:** The model filename in `assets/models/` must match the path specified in `camera_screen.dart:69`:

```dart
modelPath: 'assets/models/yolo_model.tflite',
```

### 3. Update Class Labels

Edit `camera_screen.dart` to match your model's class labels:

```dart
List<String> _getMechanicalComponentLabels() {
  return [
    'small_screw',      // Class 0
    'small_hole',       // Class 1
    'large_screw',      // Class 2
    'large_hole',       // Class 3
    'bracket',          // Class 4
    'metal_component',  // Class 5
  ];
}
```

### 4. Configure Backend URL

Update `lib/utils/api_config.dart` with your backend URL:

```dart
class ApiConfig {
  // For Android emulator accessing host machine:
  static const String baseUrl = 'http://10.0.2.2:8002';

  // For physical device on same network:
  // static const String baseUrl = 'http://192.168.1.XXX:8002';

  // For production:
  // static const String baseUrl = 'https://your-api.com';
}
```

### 5. Run on Device/Emulator

```bash
# List available devices
flutter devices

# Run on connected device
flutter run

# Run in release mode (better performance)
flutter run --release
```

## Exporting Your YOLO Model to TFLite

### From Backend

Use the backend's export utility:

```bash
cd backend
python -c "
from app.training.export import export_model_tflite
tflite_path = export_model_tflite(
    model_path='path/to/best.pt',
    output_dir='../flutter_app/assets/models',
    imgsz=640,
    int8=False  # Use FP16 for better accuracy
)
print(f'Exported to: {tflite_path}')
"
```

### Using Ultralytics

```python
from ultralytics import YOLO

# Load your trained model
model = YOLO('path/to/best.pt')

# Export to TFLite
model.export(
    format='tflite',
    imgsz=640,
    int8=False,  # FP16 quantization
    nms=True     # Include NMS in model
)
```

**Rename the exported file:**
```bash
mv best_saved_model/best_float16.tflite ../flutter_app/assets/models/yolo_model.tflite
```

## Building for Production

### Android APK

Build a release APK for distribution:

```bash
# Build APK (recommended for beta testing)
flutter build apk --release

# Output: build/app/outputs/flutter-apk/app-release.apk
```

### Android App Bundle (AAB)

Build an App Bundle for Play Store submission:

```bash
# Build App Bundle
flutter build appbundle --release

# Output: build/app/outputs/bundle/release/app-release.aab
```

### Code Signing

For production builds, you need to sign your app:

1. **Create keystore:**

```bash
keytool -genkey -v -keystore ~/yolo-vision-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias yolo-vision
```

2. **Create `android/key.properties`:**

```properties
storePassword=<your-store-password>
keyPassword=<your-key-password>
keyAlias=yolo-vision
storeFile=C:/Users/YourName/yolo-vision-key.jks
```

3. **Update `android/app/build.gradle`:**

```gradle
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    ...
    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : null
            storePassword keystoreProperties['storePassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
```

4. **Build signed APK:**

```bash
flutter build apk --release
```

## Testing on Device

### 1. Install via USB

```bash
# Connect device via USB with USB debugging enabled
flutter install

# Or manually install APK
adb install build/app/outputs/flutter-apk/app-release.apk
```

### 2. Test Camera Permissions

On first launch, the app will request camera permissions. Grant permission to use object detection.

### 3. Test Backend Connection

1. Register a new account
2. Login with credentials
3. Navigate to camera screen
4. Check for connection errors in the stats overlay

### 4. Test YOLO Detection

1. Point camera at mechanical components
2. Verify bounding boxes appear
3. Check FPS counter (target: >20 FPS)
4. Verify class labels are correct

## Performance Optimization

### Model Optimization

- **Use INT8 quantization** for faster inference (may reduce accuracy):
  ```python
  model.export(format='tflite', int8=True)
  ```

- **Reduce input size** if FPS is low:
  ```dart
  // In yolo_service.dart
  static const int inputSize = 320; // Instead of 640
  ```

### Frame Processing Optimization

Adjust frame skipping in `camera_screen.dart`:

```dart
// Process every frame (current behavior)
_cameraController!.startImageStream(_processCameraImage);

// Process every N frames (better performance)
int frameCounter = 0;
void _processCameraImage(CameraImage cameraImage) {
  if (frameCounter++ % 2 == 0) { // Skip every other frame
    if (!_isDetecting) {
      _isDetecting = true;
      final detectionProvider = Provider.of<DetectionProvider>(context, listen: false);
      detectionProvider.processFrame(cameraImage).then((_) {
        _isDetecting = false;
      });
    }
  }
}
```

## Common Issues

### Issue: "Model not found" Error

**Solution:** Verify model is in `assets/models/` and listed in `pubspec.yaml`:

```yaml
flutter:
  assets:
    - assets/models/
```

Then run:
```bash
flutter clean
flutter pub get
```

### Issue: Low FPS (<10 FPS)

**Solutions:**
1. Use INT8 quantization
2. Reduce input size to 320x320
3. Skip frames (process every 2nd or 3rd frame)
4. Build in release mode: `flutter run --release`

### Issue: Backend Connection Failed

**Solutions:**
1. Check backend is running: `http://localhost:8002/docs`
2. For emulator, use `10.0.2.2` instead of `localhost`
3. For device, ensure on same WiFi network
4. Check firewall settings

### Issue: Camera Permission Denied

**Solution:** Manually enable camera permission:
- Settings → Apps → YOLO Vision → Permissions → Camera → Allow

## Beta Distribution

### TestFlight (iOS - Future)

Not yet implemented. iOS support planned for Week 9-10.

### Firebase App Distribution (Android)

1. **Setup Firebase:**
   ```bash
   npm install -g firebase-tools
   firebase login
   firebase init hosting
   ```

2. **Upload APK:**
   ```bash
   firebase appdistribution:distribute \
     build/app/outputs/flutter-apk/app-release.apk \
     --app YOUR_FIREBASE_APP_ID \
     --groups beta-testers
   ```

### Play Store Internal Testing

1. Build App Bundle: `flutter build appbundle --release`
2. Upload to Play Console: Internal Testing track
3. Add testers via email addresses
4. Share opt-in link with testers

## Performance Targets

- **FPS:** >20 FPS on mid-range Android devices (Snapdragon 660+)
- **App Size:** <50MB APK
- **Inference Time:** <50ms per frame
- **Battery:** <10% drain per hour of continuous use

## Next Steps

After beta testing:

1. **Week 5-6:** Implement model download from backend
2. **Week 7:** Add performance profiling and optimization
3. **Week 8:** Multi-device testing (5+ different phones)
4. **Week 9-10:** iOS port and TestFlight beta

## Support

For issues or questions:
- Check `FLUTTER_IMPLEMENTATION.md` for development details
- Review backend API docs: `http://localhost:8002/docs`
- Check Flutter logs: `flutter logs`
