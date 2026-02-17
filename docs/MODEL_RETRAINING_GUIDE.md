# Model Retraining Workflow Guide
# ============================================================================
# Complete workflow for retraining YOLO models with enhanced synthetic data
# From data generation through iOS deployment
# ============================================================================

## 🚀 Overview

This guide covers the complete workflow to retrain your YOLO model with the enhanced synthetic data that addresses the issues you reported:
- ✅ Fixed small holes detection (class mapping fixed)
- ✅ Better bracket orientation handling (upside-down detection)
- ✅ Enhanced training scenarios for challenging cases

## Phase 1: Generate Enhanced Training Data

### 1.1 Test Script Changes (REQUIRED FIRST)

```bash
# Navigate to your project directory
cd "C:\path\to\your\project"

# Run validation tests
test_script_changes.bat
```

**Expected Output:**
- ✅ All tests PASSED - Script ready for data generation!

**If tests fail:** Review the console output and fix any class mapping issues before proceeding.

### 1.2 Generate Training Dataset

```bash
# Run enhanced data generation (recommended: start with smaller batch)
# Edit NUM_RENDERS in eevee_desk_scene17_dualpass.py to 50 for testing
run_memory_safe_desk_scene.bat
```

**Monitor Console for Enhanced Scenarios:**
```
🕳️  Hole-heavy scenario for enhanced small hole training
🎯 ENHANCED: Problematic orientation scenario for bracket training  
💡 ENHANCED: Specialized lighting for bracket detection training
🏆 CHALLENGE MODE: Maximum difficulty scenario for robust training
🔄 bracket_A1: Upside down (180° + 2.3°)
```

### 1.3 Validate Dataset Quality

After generation, check your output directory structure:
```
dataset_desk_mechanical_enhanced/
├── images/
│   ├── render_0000.jpg
│   ├── render_0001.jpg
│   └── ...
├── labels/
│   ├── render_0000.txt
│   ├── render_0001.txt
│   └── ...
└── debug/
    ├── render_0000_composite.jpg  # Visual verification
    └── ...
```

**Spot Check Labels:** Open a few `.txt` files and verify:
- Small holes are labeled as class `1` (not scattered across different classes)
- Bracket A objects are class `4`, Bracket B objects are class `5`
- No inconsistent class assignments

## Phase 2: Model Training (External - Use Your Preferred Framework)

### 2.1 Recommended Training Configuration

**For Ultralytics YOLOv8/v11:**
```python
from ultralytics import YOLO

# Load pretrained model
model = YOLO('yolo11n-seg.pt')  # or your preferred base model

# Train with enhanced data
results = model.train(
    data='your_dataset.yaml',  # Point to your generated dataset
    epochs=200,               # Increase epochs due to challenging scenarios
    imgsz=640,               # Match your inference size
    batch=16,                # Adjust based on GPU memory
    patience=50,             # Early stopping patience
    save_period=25,          # Save checkpoints frequently
    
    # Enhanced training for challenging cases
    mixup=0.3,               # Data augmentation for orientation variations
    copy_paste=0.3,          # Copy-paste augmentation
    mosaic=0.5,              # Mosaic augmentation
    
    # Class balancing (important for small holes)
    cls_pw=1.0,              # Class probability weight
    obj_pw=1.0,              # Object probability weight
    
    # Learning rate scheduling
    lr0=0.01,                # Initial learning rate
    lrf=0.01,                # Final learning rate fraction
    
    # Validation
    val=True,
    split='val',
    save_json=True           # Save validation results
)

# Export to Core ML
model.export(format='coreml', nms=True, imgsz=640)
```

### 2.2 Dataset Configuration (dataset.yaml)

```yaml
# dataset.yaml
path: /path/to/dataset_desk_mechanical_enhanced
train: images
val: images  # Use same folder with split or create separate val folder

# Class definitions (MUST match your fixed mappings)
names:
  0: small_screw
  1: small_hole  
  2: large_screw
  3: large_hole
  4: bracket_A
  5: bracket_B
  6: surface

# Number of classes
nc: 7
```

### 2.3 Monitor Training Progress

**Key Metrics to Watch:**
- **mAP50 for class 1 (small_hole)**: Should improve significantly
- **mAP50 for classes 4-5 (brackets)**: Look for better orientation detection
- **Precision/Recall balance**: Enhanced scenarios may initially lower precision but improve robustness

**Expected Training Phases:**
1. **Epochs 1-50**: Basic learning, mAP rising
2. **Epochs 51-100**: Refinement, challenging scenarios being learned
3. **Epochs 101-150**: Fine-tuning, enhanced scenarios mastered
4. **Epochs 151-200**: Convergence, final optimization

## Phase 3: Model Validation & Testing

### 3.1 Validate Against Known Issues

Create test images focusing on your reported problems:

1. **Small Holes Test**: Images with only small holes, no screws
2. **Bracket Orientation Test**: 
   - Normal bracket orientation
   - Upside-down brackets (180°)
   - Mixed orientations
3. **Edge Cases**: 
   - Poor lighting conditions
   - Partial occlusions
   - Material variations

### 3.2 Performance Benchmarking

```python
# Validation script example
from ultralytics import YOLO

model = YOLO('path/to/your/trained_model.pt')

# Test on validation set
results = model.val()

# Test on specific problem cases
test_results = model('path/to/test_images/')

# Check class-specific performance
print(f"Small holes mAP50: {results.results_dict['metrics/mAP50(B)'][1]}")
print(f"Bracket A mAP50: {results.results_dict['metrics/mAP50(B)'][4]}")
print(f"Bracket B mAP50: {results.results_dict['metrics/mAP50(B)'][5]}")
```

## Phase 4: iOS Deployment

### 4.1 Export to Core ML

```python
# Export trained model to Core ML
model = YOLO('path/to/best.pt')
model.export(
    format='coreml', 
    nms=True,          # Include NMS in model
    imgsz=640,         # Inference size
    int8=False,        # Use FP16 for better accuracy
    optimize=True      # Optimize for iOS
)
```

### 4.2 Replace Model in iOS Project

1. **Backup old model** in Xcode project
2. **Drag new `.mlpackage`** into Xcode project
3. **Update model name** if different:

```swift
// In your iOS code, update model name
let yolo = YOLO("your_new_model_name", task: .segment) { result in
    // Handle result
}
```

### 4.3 Test Enhanced iOS Integration

With the ComponentValidator integrated, you can now test:

```swift
// Test the enhanced business logic
let validator = ComponentValidator.standardDeskAssembly()
let validation = validator.validate(yoloResult: detectionResult)

// Check if small holes are now detected
let smallHoles = validation.detectedComponents.filter { 
    $0.componentType == .smallHole 
}
print("Small holes detected: \(smallHoles.count)")

// Check bracket orientations
let brackets = validation.detectedComponents.filter {
    $0.componentType == .bracketA || $0.componentType == .bracketB
}
for bracket in brackets {
    if let orientation = bracket.orientation {
        print("Bracket orientation: \(orientation)")
    }
}
```

## Phase 5: Validation & Debugging

### 5.1 A/B Testing Framework

Test both old and new models side-by-side:

```swift
// In your iOS app, add model comparison
struct ModelComparisonView: View {
    @State private var useNewModel = true
    
    var currentModel: String {
        useNewModel ? "enhanced_model" : "keyhole_a_b"
    }
    
    var body: some View {
        VStack {
            Toggle("Use Enhanced Model", isOn: $useNewModel)
            
            YOLOCamera(modelPathOrName: currentModel, task: .segment)
            
            if useNewModel {
                // Show ComponentValidator results
                AssemblyValidationView()
            }
        }
    }
}
```

### 5.2 Performance Monitoring

Track improvements in real-world scenarios:

```swift
// Add performance metrics
class ModelPerformanceTracker {
    func trackDetection(_ result: YOLOResult) {
        let smallHoles = result.boxes.filter { $0.cls == "small_hole" }
        let brackets = result.boxes.filter { $0.cls.contains("bracket") }
        
        // Log to analytics
        Analytics.track("detection_performance", [
            "small_holes_count": smallHoles.count,
            "brackets_count": brackets.count,
            "total_objects": result.boxes.count
        ])
    }
}
```

## 🎯 Expected Improvements

After completing this workflow, you should see:

1. **✅ Small Holes Detection**: Consistent detection and labeling of small holes
2. **✅ Bracket Orientation**: Accurate detection of upside-down brackets
3. **✅ Business Logic**: Interpretation layer provides actionable feedback
4. **✅ Robustness**: Better performance in challenging lighting/angle conditions

## 🛠 Troubleshooting Common Issues

### Issue: Small holes still not detected
**Solution**: Check dataset labels manually, ensure class 1 is consistently used

### Issue: Bracket orientations not improving
**Solution**: Increase orientation randomization probability in Blender script

### Issue: Model overfitting to synthetic data
**Solution**: Add real-world validation images, reduce model complexity

### Issue: iOS app crashes with new model
**Solution**: Check model input/output dimensions, verify Core ML export settings

## 📞 Next Steps After Retraining

1. **Validate improvements** against your original test cases
2. **Deploy enhanced iOS app** with ComponentValidator
3. **Collect real-world data** to further improve the model
4. **Iterate on training scenarios** based on new edge cases discovered

Ready to crack those "tricky scenarios with flipping upside down"! 🎉