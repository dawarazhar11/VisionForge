# Quick Start Guide - YOLO Vision App

## 🚀 Getting Started in 3 Steps

### Step 1: Start the Backend API

The Flutter app requires the backend API to be running.

**Option A: Using the batch script (Easiest)**
```batch
cd H:\Yolo Computer Vision\Baseline\backend
..\backend_venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

**Option B: Quick check if backend is running**
Open browser to: http://localhost:8002/docs
- If you see the API documentation, backend is running ✅
- If connection fails, start the backend using Option A

### Step 2: Run the Flutter App

**Windows Desktop:**
```batch
cd H:\Yolo Computer Vision\Baseline\flutter_app
build\windows\x64\runner\Release\yolo_vision_app.exe
```

**Android (via ADB):**
```batch
cd H:\Yolo Computer Vision\Baseline\flutter_app
adb install build\app\outputs\flutter-apk\app-release.apk
```

**Development Mode (Hot Reload):**
```batch
cd H:\Yolo Computer Vision\Baseline\flutter_app
flutter run -d windows
# or
flutter run -d <android-device-id>
```

### Step 3: Create Your First Account

1. **Launch the app**
2. **Click "Register"** (or "Sign Up" if on login screen)
3. **Enter your details:**
   - Email: your@email.com
   - Password: (minimum 8 characters)
   - Confirm password
4. **Click "Create Account"**
5. **Login** with your new credentials

## 📱 App Workflow

### Creating Your First Project

1. **Login** to the app
2. **Tap "+" button** or "New Project"
3. **Enter Project Details:**
   - Name: "My First Detection Project"
   - Description: Optional
4. **Click "Create"**

### Adding Training Data

**Option 1: Upload Images (Manual)**
1. Open your project
2. Go to **Datasets** tab
3. Click **"Upload Dataset"**
4. Select images (JPG/PNG)
5. Optionally add annotation files (.txt in YOLO format)

**Option 2: Camera Capture & Annotate**
1. Open your project
2. Go to **Datasets** tab
3. Click **"Capture & Annotate"**
4. Take photos with device camera
5. Draw bounding boxes on objects
6. Label each box
7. Save annotations

**Option 3: Generate Synthetic Data (Blender)**
1. Open your project
2. Go to **Datasets** tab
3. Click **"Generate Synthetic Data"**
4. Upload a Blender `.blend` file
5. Configure number of renders
6. Click **"Start Generation"**

### Training a Model

1. **Open your project**
2. Go to **Training** tab
3. Click **"Start Training"** or **"New Training Job"**
4. **Configure training:**
   - Model Type: Detection, Segmentation, Classification
   - Base Model: YOLOv11n, YOLOv11s, etc.
   - Dataset: Select uploaded dataset
   - Epochs: 50-100 (recommended)
   - Batch Size: 16 (adjust for GPU)
   - Image Size: 640
5. Click **"Start Training"**
6. **Monitor progress** in Training Jobs screen

### Using a Trained Model

1. **Go to "My Models"** screen
2. **Find your trained model**
3. Click **"Download"** to save locally
4. Click **"Set Active"** to use for detection
5. **Go to Detection screen**
6. Point camera at objects
7. See real-time detections!

## 🔍 Troubleshooting

### "Unable to connect to server"
**Problem:** Backend API is not running

**Solution:**
```batch
cd H:\Yolo Computer Vision\Baseline\backend
..\backend_venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```
Keep this terminal open while using the app.

### "Cannot create project" / "Authentication failed"
**Problem:** Database not initialized or user not registered

**Solution:**
1. Check backend terminal for errors
2. Ensure you've registered an account
3. Try logging out and back in
4. Restart backend if needed

### "No camera detected"
**Problem:** Camera permissions not granted

**Solution:**
- **Windows:** Check Windows Settings → Privacy → Camera
- **Android:** Go to App Settings → Permissions → Enable Camera
- **iOS:** Settings → Privacy → Camera → Enable for app

### "Model loading failed"
**Problem:** YOLO model not downloaded or incompatible format

**Solution:**
1. Ensure model is downloaded (check "My Models")
2. Verify model format:
   - Android: `.tflite`
   - Windows: `.onnx` (planned)
   - iOS: `.mlmodel` (planned)
3. Currently using placeholder - implement TFLite/ONNX/CoreML integration

### Backend Database Error
**Problem:** Database not set up

**Solution:**
```batch
cd H:\Yolo Computer Vision\Baseline\backend
..\backend_venv\Scripts\alembic.exe upgrade head
```

## 📊 Backend API Endpoints

Access API documentation at: **http://localhost:8002/docs**

**Key Endpoints:**
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `POST /api/datasets/upload` - Upload dataset
- `POST /api/training/jobs` - Start training
- `GET /api/training/jobs` - List training jobs
- `GET /api/models` - List trained models

## 🎯 Quick Demo Workflow

**Complete end-to-end test (5 minutes):**

```batch
# 1. Start backend
cd H:\Yolo Computer Vision\Baseline\backend
start ..\backend_venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002

# 2. Run Flutter app
cd ..\flutter_app
start build\windows\x64\runner\Release\yolo_vision_app.exe

# 3. In the app:
# - Register new account
# - Create project "Test Project"
# - Upload some images (or use camera)
# - Start training job
# - Monitor progress
# - Download trained model
# - Test detection with camera
```

## 💾 Data Storage Locations

**Backend:**
- Database: `backend/yolo_vision.db` (SQLite)
- Uploaded files: `backend/uploads/`
- Trained models: `backend/models/`
- Datasets: `backend/datasets/`

**Flutter App:**
- Downloaded models: `<app-documents>/models/`
- Cached data: `<app-documents>/cache/`
- Settings: SharedPreferences

## 🔐 Default Configuration

**API Server:**
- URL: `http://localhost:8002`
- Change in: `flutter_app/lib/utils/api_config.dart`

**Database:**
- Type: SQLite
- Location: `backend/yolo_vision.db`

**Training:**
- Default epochs: 50
- Default batch size: 16
- Default image size: 640x640

## 📱 Platform-Specific Notes

### Windows
- Camera requires USB webcam or integrated camera
- Models stored in: `%USERPROFILE%\Documents\yolo_vision_app\models`

### Android
- Requires Android 6.0+ (API level 23+)
- Camera permission must be granted
- Models stored in app's private storage

### iOS (When Built)
- Requires iOS 12.0+
- Camera permission in Settings
- Uses CoreML for inference

## 🆘 Need Help?

**Backend Issues:**
Check logs at: `backend/logs/` (if logging configured)

**Flutter App Issues:**
- Check console output when running with `flutter run`
- Enable debug mode in Settings

**Training Issues:**
- Ensure sufficient GPU memory (4GB+ recommended)
- Reduce batch size if OOM errors
- Check dataset format (YOLO format required)

**API Testing:**
Use the Swagger UI at http://localhost:8002/docs to test endpoints directly.

## 🚀 Next Steps

1. **Test the complete workflow** with sample data
2. **Customize model architecture** in training config
3. **Export models** to different formats (TFLite, ONNX, CoreML)
4. **Deploy backend** to cloud (see PRODUCTION_CHECKLIST.md)
5. **Publish apps** to stores (Android: Play Store, iOS: App Store)

## 📚 Additional Resources

- **Backend API Docs:** `backend/API_DOCUMENTATION.md`
- **Training Guide:** `backend/TRAINING_QUICKSTART.md`
- **iOS Build:** `flutter_app/IOS_BUILD_GUIDE.md`
- **Windows Desktop:** `flutter_app/WINDOWS_DESKTOP_GUIDE.md`
