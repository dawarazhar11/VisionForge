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

### iOS App

Build an iOS app for device testing and App Store submission:

#### Quick iOS Build Checklist

- [ ] macOS with Xcode 14.0+ installed
- [ ] Apple Developer account enrolled
- [ ] CocoaPods installed: `sudo gem install cocoapods`
- [ ] Camera permissions added to `Info.plist`
- [ ] Bundle identifier configured in Xcode
- [ ] Code signing configured (automatic or manual)
- [ ] TFLite model in `assets/models/`
- [ ] Physical iOS device for testing (simulator doesn't support camera well)

#### Prerequisites for iOS

- macOS with Xcode 14.0 or higher
- Apple Developer account ($99/year for distribution)
- CocoaPods installed: `sudo gem install cocoapods`
- Physical iOS device (iOS 12.0+) or Simulator

#### iOS Setup Steps

1. **Install CocoaPods dependencies:**

```bash
cd flutter_app/ios
pod install
cd ..
```

2. **Configure iOS permissions in `ios/Runner/Info.plist`:**

The camera permission is required. Add this if not present:

```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to detect mechanical components using YOLO object detection.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>This app needs photo library access to save detection results.</string>
```

3. **Update Bundle Identifier:**

Open `ios/Runner.xcworkspace` in Xcode and:
- Select the Runner project
- Go to Signing & Capabilities
- Set a unique Bundle Identifier (e.g., `com.yourcompany.yolovision`)
- Select your Development Team

4. **Configure minimum iOS version:**

In `ios/Podfile`, ensure minimum version is set:

```ruby
platform :ios, '12.0'
```

#### Build iOS IPA for Testing

```bash
# Build for connected device (development)
flutter build ios --release

# Build IPA for distribution (requires proper signing)
flutter build ipa --release

# Output: build/ios/ipa/yolo_vision.ipa
```

#### Run on iOS Device/Simulator

```bash
# List available iOS devices
flutter devices

# Run on connected iPhone
flutter run -d <device-id>

# Run on simulator
open -a Simulator
flutter run
```

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

#### iOS Code Signing

iOS apps require proper code signing for distribution:

1. **Automatic Signing (Recommended for Development):**

Open `ios/Runner.xcworkspace` in Xcode:
- Select Runner project → Signing & Capabilities
- Check "Automatically manage signing"
- Select your Apple Developer Team
- Xcode will handle provisioning profiles

2. **Manual Signing (For Distribution):**

```bash
# Create App Store provisioning profile in Apple Developer Portal
# Download and install the profile
# In Xcode: Uncheck "Automatically manage signing"
# Select the provisioning profile manually
```

3. **Build signed IPA:**

```bash
# Archive and export IPA
flutter build ipa --release

# Or use Xcode:
# Product → Archive → Distribute App
```

#### Android Code Signing

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
storeFile=/Users/YourName/yolo-vision-key.jks
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

### iOS-Specific Issues

#### Issue: "No provisioning profiles found"

**Solution:** 
1. Open `ios/Runner.xcworkspace` in Xcode
2. Select Runner project → Signing & Capabilities
3. Enable "Automatically manage signing"
4. Select your Apple Developer Team
5. If still failing, manually create provisioning profile in Apple Developer Portal

#### Issue: CocoaPods dependency errors

**Solution:**
```bash
cd ios
pod deintegrate
pod cache clean --all
pod install
cd ..
flutter clean
flutter pub get
```

#### Issue: "Module 'tflite_flutter' not found"

**Solution:**
Ensure TFLite plugin is properly configured for iOS:
```bash
flutter clean
cd ios
pod install
cd ..
flutter build ios
```

#### Issue: Camera doesn't work on iOS Simulator

**Note:** Camera detection requires a physical iOS device. The simulator doesn't support camera functionality properly.

**Solution:** Test on a real iPhone/iPad connected via USB or wirelessly.

#### Issue: "Unsupported Architecture" when building for device

**Solution:**
In `ios/Podfile`, ensure proper architecture settings:
```ruby
post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['ONLY_ACTIVE_ARCH'] = 'NO'
      config.build_settings['EXCLUDED_ARCHS[sdk=iphonesimulator*]'] = 'arm64'
    end
  end
end
```

### Android & iOS Common Issues

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
5. **iOS:** Consider using Core ML instead of TFLite for better performance

### Issue: Backend Connection Failed

**Solutions:**
1. Check backend is running: `http://localhost:8002/docs`
2. **Android emulator:** Use `10.0.2.2` instead of `localhost`
3. **iOS simulator:** Use your Mac's local IP or `localhost`
4. **Physical device:** Ensure on same WiFi network
5. Check firewall settings
6. For iOS, ensure App Transport Security allows your backend URL

### Issue: Camera Permission Denied

**Android Solution:** 
- Settings → Apps → YOLO Vision → Permissions → Camera → Allow

**iOS Solution:**
- Settings → YOLO Vision → Camera → Enable
- Ensure `NSCameraUsageDescription` is in `Info.plist`

## Beta Distribution

### TestFlight (iOS)

TestFlight is Apple's beta testing platform integrated with App Store Connect.

1. **Archive your app in Xcode:**

```bash
# Build IPA
flutter build ipa --release

# Or use Xcode:
# Open ios/Runner.xcworkspace
# Product → Archive
```

2. **Upload to App Store Connect:**

**Option A: Using Xcode**
- After archiving, Window → Organizer
- Select your archive
- Click "Distribute App"
- Choose "TestFlight & App Store"
- Follow the wizard to upload

**Option B: Using Transporter app**
- Download Transporter from Mac App Store
- Drag and drop the `.ipa` file
- Click "Deliver"

**Option C: Using command line**
```bash
# Install fastlane
sudo gem install fastlane

# Initialize fastlane
cd ios
fastlane init

# Upload to TestFlight
fastlane pilot upload --ipa ../build/ios/ipa/yolo_vision.ipa
```

3. **Add testers in App Store Connect:**
- Go to TestFlight tab
- Add internal testers (up to 100)
- Add external testers (requires Beta App Review)
- Testers receive email invitation

4. **Enable beta testing:**
- Wait for processing (usually 10-30 minutes)
- Provide export compliance information
- Submit for Beta App Review (external testers only)

**Important iOS-specific considerations:**
- First upload requires full metadata in App Store Connect
- Camera usage description must be clear and justified
- TFLite model should be optimized for iOS (use Core ML if possible)

### Firebase App Distribution (Android & iOS)

Firebase App Distribution works for both platforms:

1. **Setup Firebase:**
   ```bash
   npm install -g firebase-tools
   firebase login
   firebase init hosting
   ```

2. **Upload APK (Android):**
   ```bash
   firebase appdistribution:distribute \
     build/app/outputs/flutter-apk/app-release.apk \
     --app YOUR_FIREBASE_ANDROID_APP_ID \
     --groups beta-testers
   ```

3. **Upload IPA (iOS):**
   ```bash
   firebase appdistribution:distribute \
     build/ios/ipa/yolo_vision.ipa \
     --app YOUR_FIREBASE_IOS_APP_ID \
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
3. **Week 8:** Multi-device testing (5+ different phones, both iOS and Android)
4. **Week 9:** iOS optimization with Core ML conversion
5. **Week 10:** Production release to App Store and Play Store

### Optional iOS Performance Enhancement: Core ML

For better iOS performance, consider converting your TFLite model to Core ML:

```python
# Install coremltools
pip install coremltools

# Convert YOLO model to Core ML
import coremltools as ct
from ultralytics import YOLO

# Load and export
model = YOLO('path/to/best.pt')
model.export(format='coreml', nms=True)

# This creates a .mlpackage that can be used directly in iOS
```

Then update your Flutter app to use Core ML on iOS and TFLite on Android for optimal performance.

## Support

For issues or questions:
- Check `FLUTTER_IMPLEMENTATION.md` for development details
- Review backend API docs: `http://localhost:8002/docs`
- Check Flutter logs: `flutter logs`
