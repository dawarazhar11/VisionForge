# iOS Build Guide

## Prerequisites

**Required Environment:**
- macOS 10.15 (Catalina) or later
- Xcode 13.0 or later (from Mac App Store)
- Flutter SDK installed and configured
- CocoaPods installed (`sudo gem install cocoapods`)
- An Apple Developer account (for device deployment)

**Verify Prerequisites:**
```bash
flutter doctor -v
pod --version
xcodebuild -version
```

## iOS Configuration

The iOS project is already configured with:

### 1. Permissions (Info.plist)
All required permissions are configured:
- **NSCameraUsageDescription**: Real-time object detection with YOLO models
- **NSPhotoLibraryUsageDescription**: Select images for detection and annotation
- **NSPhotoLibraryAddUsageDescription**: Save annotated images
- **NSMicrophoneUsageDescription**: Video recording features

### 2. Podfile
CocoaPods dependency management configured:
- iOS deployment target: 12.0
- Plugin dependencies: camera, permission_handler, path_provider, file_picker, shared_preferences
- Bitcode disabled for compatibility

### 3. Project Structure
```
flutter_app/ios/
├── Runner/
│   ├── Info.plist          ✓ Configured
│   ├── AppDelegate.swift   ✓ Standard Flutter delegate
│   └── Assets.xcassets     ✓ App icons
├── Runner.xcodeproj/       ✓ Xcode project
├── Podfile                 ✓ Created
└── Flutter/
    ├── Debug.xcconfig      ✓ Debug configuration
    └── Release.xcconfig    ✓ Release configuration
```

## Build Instructions

### Step 1: Navigate to Project Directory
```bash
cd "path/to/flutter_app"
```

### Step 2: Install Flutter Dependencies
```bash
flutter pub get
```

### Step 3: Install CocoaPods Dependencies
```bash
cd ios
pod install
cd ..
```

This will create `Pods/` directory and `Runner.xcworkspace`.

### Step 4: Build for iOS Simulator (Testing)
```bash
flutter build ios --simulator
```

Or run directly in simulator:
```bash
flutter run -d simulator
```

### Step 5: Build for iOS Device (Release)

**Important:** Requires code signing setup in Xcode.

```bash
# Open Xcode to configure signing
open ios/Runner.xcworkspace
```

In Xcode:
1. Select **Runner** target
2. Go to **Signing & Capabilities**
3. Select your **Team** (Apple Developer account)
4. Ensure **Bundle Identifier** is unique (e.g., `com.yourcompany.yolovisionapp`)
5. Enable **Automatic signing** or configure **Manual signing**

Then build:
```bash
flutter build ios --release
```

### Step 6: Create IPA for Distribution

**Archive the app:**
```bash
flutter build ipa
```

This creates: `build/ios/archive/Runner.xcarchive`

**Or manually in Xcode:**
1. Open `ios/Runner.xcworkspace`
2. Product → Archive
3. Window → Organizer
4. Select archive → **Distribute App**
5. Choose distribution method (App Store, Ad Hoc, Enterprise, Development)

## Common Issues

### Issue 1: CocoaPods Not Found
```bash
sudo gem install cocoapods
pod setup
```

### Issue 2: Code Signing Errors
- Ensure you're logged into Xcode with Apple ID (Preferences → Accounts)
- Check Bundle Identifier is unique
- Verify provisioning profiles are valid

### Issue 3: Pod Install Fails
```bash
cd ios
pod repo update
pod install --repo-update
cd ..
```

### Issue 4: Build Fails with Plugin Errors
```bash
flutter clean
flutter pub get
cd ios
rm -rf Pods/ Podfile.lock
pod install
cd ..
flutter build ios
```

## Deployment Targets

### iOS Simulator
- Fastest for development testing
- No code signing required
- Available on any Mac with Xcode

**List available simulators:**
```bash
xcrun simctl list devices
```

**Run on specific simulator:**
```bash
flutter run -d "iPhone 14 Pro"
```

### Physical iOS Device
- Required for testing camera, AR, and performance
- Requires Apple Developer account ($99/year)
- Requires USB connection or wireless debugging

**Connect device and run:**
```bash
flutter devices  # List connected devices
flutter run -d [device-id]
```

### TestFlight (Beta Testing)
1. Build IPA: `flutter build ipa`
2. Upload to App Store Connect via Xcode Organizer or Transporter app
3. Configure TestFlight beta testing
4. Send invites to beta testers

### App Store Distribution
1. Build release IPA: `flutter build ipa --release`
2. Submit via Xcode Organizer or Application Loader
3. Complete App Store Connect listing
4. Submit for review
5. Publish after approval

## Build Configurations

### Debug Build (Development)
```bash
flutter build ios --debug
flutter run --debug
```
- Includes debugging symbols
- Larger app size
- Slower performance
- Hot reload enabled

### Profile Build (Performance Testing)
```bash
flutter build ios --profile
flutter run --profile
```
- Performance optimization enabled
- Debugging symbols included
- Used for performance profiling

### Release Build (Production)
```bash
flutter build ios --release
```
- Maximum optimization
- No debugging symbols
- Smallest app size
- Best performance

## File Sizes and Requirements

**Expected Build Sizes:**
- Debug build: ~150-200 MB
- Release build: ~50-80 MB
- IPA archive: ~30-50 MB (compressed)

**iOS Version Support:**
- Minimum: iOS 12.0
- Recommended target: iOS 15.0+
- Latest tested: iOS 17.x

**Device Compatibility:**
- iPhone 6s and newer
- iPad Air 2 and newer
- iPad Pro (all models)
- iPad mini 4 and newer

## App Store Submission Checklist

- [ ] Update version in `pubspec.yaml`
- [ ] Update build number for each submission
- [ ] Test on multiple devices (iPhone, iPad)
- [ ] Test all permissions (camera, photo library)
- [ ] Prepare app screenshots (required sizes)
- [ ] Create app icon (1024x1024 for App Store)
- [ ] Write App Store description
- [ ] Set privacy policy URL (if collecting data)
- [ ] Configure age rating
- [ ] Complete export compliance documentation

## Next Steps

1. **On macOS:** Run `pod install` in `ios/` directory
2. **Open Xcode:** `open ios/Runner.xcworkspace`
3. **Configure Signing:** Set team and bundle identifier
4. **Test Build:** Run on simulator first
5. **Device Testing:** Test on physical iOS device
6. **Production Build:** Create release IPA for distribution

## Support

For Flutter-specific issues:
- Flutter documentation: https://flutter.dev/docs
- iOS deployment: https://flutter.dev/docs/deployment/ios

For Xcode and App Store issues:
- Apple Developer: https://developer.apple.com
- App Store Connect: https://appstoreconnect.apple.com
