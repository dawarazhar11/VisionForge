# 📱 iOS Model Update Guide

This guide shows how to update your iOS app to use a newly trained YOLO model.

## Step 1: Verify Model Export

After running `train_and_deploy.bat`, check that your new model is in the iOS project:

```bash
ls -la "yolo-ios-app/YOLOiOSApp/YOLOiOSApp/"
```

You should see: `mechanical_components_v1.mlpackage`

## Step 2: Update iOS Code

### 2.1 Open Xcode Project
```bash
open yolo-ios-app/YOLOiOSApp/YOLOiOSApp.xcodeproj
```

### 2.2 Update Model Name in YOLO.swift

Find the YOLO initialization in `Sources/YOLO/YOLO.swift`:

**Before (current default):**
```swift
let yolo = YOLO(modelPathOrName: "keyhole_a_b")
```

**After (your new model):**
```swift
let yolo = YOLO(modelPathOrName: "mechanical_components_v1")
```

### 2.3 Update Class Names (if needed)

If your class names changed, update them in the YOLO predictor files to match your training data:

```swift
// In your predictor class, ensure class names match:
let classNames = [
    "small_screw",
    "small_hole", 
    "large_screw",
    "large_hole",
    "bracket_A",
    "bracket_B",
    "surface"
]
```

## Step 3: Test the Updated App

### 3.1 Build and Run on Simulator
```bash
cd yolo-ios-app
swift build
```

### 3.2 Test on Real Device

1. Connect iOS device
2. In Xcode: Product → Destination → Your Device
3. Product → Run (Cmd+R)
4. Allow camera permissions
5. Point camera at mechanical components

### 3.3 Performance Testing

Monitor performance using Xcode Instruments:
- Check inference time (should be <100ms)
- Monitor memory usage
- Verify accuracy on real components

## Step 4: Compare Model Performance

### 4.1 A/B Test Models

You can easily switch between models for comparison:

```swift
// Test with old model
let yolo_old = YOLO(modelPathOrName: "keyhole_a_b")

// Test with new model  
let yolo_new = YOLO(modelPathOrName: "mechanical_components_v1")
```

### 4.2 Performance Metrics to Check

- **Inference Speed**: <100ms per frame for real-time
- **Detection Accuracy**: Test on real mechanical parts
- **Memory Usage**: <200MB typical
- **Battery Impact**: Monitor during extended use

## Step 5: Production Deployment

### 5.1 Update App Version

In `Info.plist`:
- Increment `CFBundleShortVersionString` (user-facing version)
- Increment `CFBundleVersion` (build number)

### 5.2 Archive for App Store

```bash
# Clean build
xcodebuild clean -project yolo-ios-app/YOLOiOSApp/YOLOiOSApp.xcodeproj

# Archive
xcodebuild archive \
  -project yolo-ios-app/YOLOiOSApp/YOLOiOSApp.xcodeproj \
  -scheme YOLOiOSApp \
  -archivePath YOLOiOSApp.xcarchive
```

## Troubleshooting

### Model Loading Issues

```swift
// Add debug logging to check model loading
guard let modelURL = Bundle.main.url(forResource: "mechanical_components_v1", 
                                   withExtension: "mlpackage") else {
    print("❌ Model file not found in bundle")
    return
}
print("✅ Model found at: \(modelURL)")
```

### Performance Issues

- **Too slow?** Reduce image resolution or use smaller model (yolo11n vs yolo11s)
- **Too big?** Check model size and consider quantization
- **Memory issues?** Profile with Xcode Instruments

### Accuracy Issues

- **Missing detections?** Lower confidence threshold
- **False positives?** Raise confidence threshold or retrain with more background images
- **Wrong classes?** Verify class mapping matches training data

## Model Management

### Version Control

Keep track of your models:

```
yolo-ios-app/YOLOiOSApp/YOLOiOSApp/
├── keyhole_a_b.mlpackage              # Original model
├── mechanical_components_v1.mlpackage  # Your new model
├── mechanical_components_v2.mlpackage  # Future iterations
```

### Rollback Strategy

To rollback to previous model:
1. Change model name back in YOLO.swift
2. Rebuild and test
3. Archive new version if needed

## Success Checklist

- [ ] Model exported to iOS project directory
- [ ] Model name updated in YOLO.swift
- [ ] App builds without errors
- [ ] Camera permissions granted
- [ ] Real-time inference working (<100ms)
- [ ] Detections accurate on real components
- [ ] Memory usage acceptable
- [ ] Ready for App Store submission

Your mechanical components detection app should now be using your custom-trained model! 🎉