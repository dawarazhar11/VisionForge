# 🖥️ iOS Simulator Testing Guide

## Quick Start (5 minutes)

### Option 1: Automatic (Recommended)

```bash
# 1. Open terminal and navigate to project
cd /Users/dawarazhar/Documents/yolo-computer-vision-baseline/flutter_app

# 2. Run app (simulator opens automatically)
flutter run

# That's it! App will:
# - Open iOS Simulator
# - Install the app
# - Launch automatically
```

### Option 2: Manual Control

```bash
# 1. Open Simulator first
open -a Simulator

# 2. Wait for simulator to boot (~10 seconds)

# 3. Run Flutter app
cd /Users/dawarazhar/Documents/yolo-computer-vision-baseline/flutter_app
flutter run -d "iPhone 15 Pro"
```

---

## 📍 File Locations

### Build Artifacts

```
Simulator Build:
├── Location: build/ios/iphonesimulator/Runner.app
├── Size: ~150-200 MB
├── Platform: x86_64/arm64 (simulator)
└── Usage: Testing in iOS Simulator

Device Build (Physical iPhone/iPad):
├── Command: flutter build ios --release
├── Location: build/ios/iphoneos/Runner.app
├── Size: ~50-80 MB (optimized)
├── Platform: arm64 (actual iOS devices)
└── Usage: Deploy to physical iPhone/iPad

App Store Build (IPA):
├── Command: flutter build ipa --release
├── Location: build/ios/ipa/yolo_vision.ipa
├── Size: ~30-50 MB (compressed)
└── Usage: TestFlight, App Store distribution
```

### Full Paths

```bash
# Current simulator build (just created)
/Users/dawarazhar/Documents/yolo-computer-vision-baseline/flutter_app/build/ios/iphonesimulator/Runner.app

# Future device build
/Users/dawarazhar/Documents/yolo-computer-vision-baseline/flutter_app/build/ios/iphoneos/Runner.app

# Future IPA for distribution
/Users/dawarazhar/Documents/yolo-computer-vision-baseline/flutter_app/build/ios/ipa/yolo_vision.ipa
```

---

## 🎮 Simulator Controls

### Common Operations

#### Device Selection
```bash
# List all available simulators
xcrun simctl list devices

# Example output:
# -- iOS 17.2 --
#     iPhone SE (3rd generation) (UDID) (Shutdown)
#     iPhone 15 (UDID) (Shutdown)
#     iPhone 15 Pro (UDID) (Shutdown)
#     iPad Pro 11-inch (4th generation) (UDID) (Shutdown)

# Boot specific device
xcrun simctl boot "iPhone 15 Pro"
```

#### Keyboard Shortcuts in Simulator
```
Home Button:           Cmd + Shift + H
Lock Screen:           Cmd + L
Screenshot:            Cmd + S
Rotate Left:           Cmd + Left Arrow
Rotate Right:          Cmd + Right Arrow
Shake Gesture:         Ctrl + Cmd + Z
Toggle Keyboard:       Cmd + K
```

#### Simulate Physical Device Features
```
Hardware Menu:
├── Shake Gesture          (Ctrl + Cmd + Z)
├── Rotation               (Cmd + Arrow Keys)
├── Home Button            (Cmd + Shift + H)
├── Volume Up/Down         (Buttons in simulator)
└── Screenshot             (Cmd + S)

Features Menu:
├── Location               → Simulate GPS coordinates
├── Face ID / Touch ID     → Simulate biometric auth
├── Low Power Mode         → Test battery optimization
└── Appearance             → Toggle Light/Dark mode
```

---

## 🧪 Testing Your App on Simulator

### Complete Test Flow

#### 1. **Launch Simulator**
```bash
# Terminal 1: Start simulator
open -a Simulator

# Wait ~10 seconds for boot

# Terminal 2: Run app
cd flutter_app
flutter run
```

#### 2. **First Launch - Grant Permissions**
When app first opens, you'll see permission prompts:

```
Camera Permission:
├── "YOLO Vision would like to access the camera"
├── Choose: "Allow"
└── ⚠️ Note: Simulator camera shows black screen (no actual camera)

Photo Library Permission:
├── "YOLO Vision would like to access your photos"
├── Choose: "Allow Access to All Photos"
└── Needed for dataset upload

Notifications (if implemented):
├── "YOLO Vision would like to send notifications"
└── Choose: "Allow"
```

#### 3. **Navigation Test**
Test all screens:

```
✅ Authentication
├── Register new account
├── Login with credentials
└── Verify auto-login on restart

✅ Projects
├── Create new project
├── View project list
├── Open project details
└── Delete project

✅ Blender Upload
├── Select .blend file (use Files app in simulator)
├── Configure rendering parameters
├── Upload and monitor progress
└── Verify dataset creation

✅ Datasets
├── View uploaded datasets
├── Preview images
├── Check annotations
└── Delete datasets

✅ Training Jobs
├── Create training job
├── Configure hyperparameters
├── Submit job
├── Monitor progress
└── Download trained model

✅ Detection
├── Camera preview (black in simulator)
├── Load model
├── Start detection
└── View results (use static images instead)

✅ Settings
├── Update user profile
├── View account info
├── Logout
└── App configuration
```

#### 4. **Hot Reload Testing**
While app is running:

```bash
# Make code changes in your editor

# Then in terminal with running app:
r    # Hot reload (fast, preserves state)
R    # Hot restart (slower, fresh start)
q    # Quit and stop app
```

---

## 📷 Camera Limitation in Simulator

### ⚠️ Important Note
**iOS Simulator does NOT have a real camera**

#### What This Means:
```
Camera Screen:
├── Opens successfully ✓
├── Shows black screen (no camera feed)
├── Detection can't run (no images to process)
└── Need physical device for full camera testing
```

#### Workaround for Testing:
```dart
// Instead of camera detection, test with static images:

1. Use Image Upload:
   ├── Go to Detection screen
   ├── Use "Select Image" instead of camera
   ├── Choose from photo library
   └── Run detection on static image

2. Use Sample Images:
   ├── Add test images to simulator Photos
   ├── Settings → Photos → Sync Sample Photos
   └── Test detection on these images
```

#### For Full Camera Testing:
```
✅ Use Physical iPhone/iPad:
├── Build: flutter build ios --release
├── Deploy via Xcode
├── Test real-time camera detection
└── Verify FPS and performance
```

---

## 🔧 Troubleshooting

### Simulator Won't Boot
```bash
# Reset simulator
xcrun simctl erase "iPhone 15 Pro"

# Or delete and recreate
xcrun simctl delete "iPhone 15 Pro"
xcrun simctl create "iPhone 15 Pro" "com.apple.CoreSimulator.SimDeviceType.iPhone-15-Pro"
```

### App Won't Install
```bash
# Clean and rebuild
flutter clean
flutter pub get
flutter run
```

### Black Screen on Launch
```bash
# Check console for errors
flutter logs

# Or rebuild in debug mode
flutter run --debug
```

### Slow Performance
```bash
# Run in release mode
flutter run --release

# Or increase simulator performance:
# Simulator → Window → Physical Size (instead of Pixel Accurate)
```

---

## 📱 Testing on Physical iPhone/iPad

### Prerequisites
- ✅ iPhone/iPad (iOS 13.0+)
- ✅ USB cable or Wi-Fi connection
- ✅ Apple Developer account (free or paid)
- ✅ Xcode configured

### Steps

#### 1. **Configure Xcode Signing**
```bash
# Open Xcode workspace
cd flutter_app/ios
open Runner.xcworkspace
```

In Xcode:
1. Select **Runner** project
2. Go to **Signing & Capabilities** tab
3. Select your **Team** (Apple ID)
4. Set unique **Bundle Identifier**:
   ```
   com.yourcompany.yolovision
   ```
5. Enable **Automatically manage signing**

#### 2. **Connect iPhone**
```bash
# Connect via USB cable
# Or enable Wi-Fi debugging:
# Xcode → Window → Devices and Simulators → Connect via Network
```

#### 3. **Trust Computer on iPhone**
```
1. Connect iPhone
2. iPhone shows: "Trust This Computer?"
3. Tap "Trust"
4. Enter iPhone passcode
```

#### 4. **Run on Device**
```bash
# Terminal
cd flutter_app

# List connected devices
flutter devices

# Output shows:
# iPhone (mobile) • 00008XXX-XXXXXX • ios • iOS 17.2

# Run on iPhone
flutter run -d "iPhone"

# Or specify device ID
flutter run -d 00008XXX-XXXXXX
```

#### 5. **First Install - Trust Developer**
On iPhone:
```
1. App tries to launch
2. Shows "Untrusted Developer"
3. Go to: Settings → General → VPN & Device Management
4. Tap your Apple ID
5. Tap "Trust"
6. Rerun: flutter run -d "iPhone"
```

---

## 🎯 Performance Testing

### FPS Targets

```
iOS Simulator (Approximate):
├── Debug Mode:     5-10 FPS
├── Release Mode:   10-15 FPS
└── Note: Much slower than real device

Physical iPhone:
├── Debug Mode:     15-20 FPS
├── Release Mode:   25-30 FPS
└── Goal: >20 FPS for smooth detection

Optimization Tips:
├── Always test performance on physical device
├── Use release mode: flutter run --release
├── Profile with: flutter run --profile
└── Monitor with Xcode Instruments
```

### Performance Commands

```bash
# Profile mode (for performance testing)
flutter run --profile -d "iPhone"

# Release mode (production performance)
flutter run --release -d "iPhone"

# Debug mode (development, slower)
flutter run --debug -d "iPhone"
```

---

## 📊 Monitoring & Debugging

### Real-time Logs
```bash
# View app logs
flutter logs

# Filter logs
flutter logs | grep "YOLO"

# Save logs to file
flutter logs > app_logs.txt
```

### Performance Overlay
```dart
// In app, enable performance overlay:
// Show FPS, GPU usage, memory

Settings → Developer Options → Performance Overlay
```

### Xcode Instruments
```bash
# Profile with Xcode
open ios/Runner.xcworkspace

# Run → Profile
# Choose instrument:
# - Time Profiler (CPU usage)
# - Allocations (Memory usage)
# - Leaks (Memory leaks)
# - Energy Log (Battery impact)
```

---

## 🚀 Quick Commands Reference

### Simulator
```bash
# Launch app on simulator
flutter run

# Specific device
flutter run -d "iPhone 15 Pro"

# Release mode
flutter run --release

# Hot reload
r

# Hot restart
R

# Quit
q
```

### Physical Device
```bash
# List devices
flutter devices

# Run on iPhone
flutter run -d "iPhone"

# Build only (no run)
flutter build ios --release

# Create IPA
flutter build ipa --release
```

### Simulator Management
```bash
# List simulators
xcrun simctl list devices

# Boot simulator
xcrun simctl boot "iPhone 15 Pro"

# Open Simulator app
open -a Simulator

# Reset simulator
xcrun simctl erase "iPhone 15 Pro"

# Delete all unavailable simulators
xcrun simctl delete unavailable
```

### Build Management
```bash
# Clean build
flutter clean

# Get dependencies
flutter pub get

# Upgrade packages
flutter pub upgrade

# Check for issues
flutter doctor

# Analyze code
flutter analyze
```

---

## ✅ Testing Checklist

### Simulator Testing
- [ ] App launches successfully
- [ ] All screens navigate correctly
- [ ] Authentication works (register/login)
- [ ] Projects CRUD operations
- [ ] Blender file selection (Files app)
- [ ] Training job creation
- [ ] UI rendering correct
- [ ] No crashes or errors
- [ ] Logs show no warnings

### Device Testing (Required for Full Validation)
- [ ] App installs on iPhone
- [ ] Camera opens and shows feed
- [ ] Real-time detection works
- [ ] FPS acceptable (>20)
- [ ] Battery usage reasonable
- [ ] No thermal throttling
- [ ] Network calls work
- [ ] Background processing works
- [ ] App resume after background
- [ ] Notifications work

---

## 🎉 You're Ready!

### Current Status:
✅ App built for simulator
✅ Blender upload integrated
✅ Training commands functional
✅ All 13 CocoaPods installed
✅ TensorFlow Lite ready
✅ Full feature set available

### Next Steps:
1. **Run on simulator:** `flutter run`
2. **Test all features** (except camera)
3. **Deploy to iPhone** for camera testing
4. **Upload real .blend file**
5. **Train your first model**
6. **Test real-time detection**

**Your professional ML training pipeline is ready to use!** 🚀

---

## 📚 Additional Resources

### Simulator Documentation
- Apple: https://developer.apple.com/documentation/xcode/running-your-app-in-the-simulator
- Flutter: https://flutter.dev/docs/get-started/install/macos#ios-setup

### Device Testing
- Flutter iOS: https://flutter.dev/docs/deployment/ios
- App Signing: https://developer.apple.com/support/code-signing/

### Performance
- Flutter Performance: https://flutter.dev/docs/perf
- Xcode Instruments: https://developer.apple.com/documentation/xcode/instruments

---

**Happy Testing! 📱✨**
