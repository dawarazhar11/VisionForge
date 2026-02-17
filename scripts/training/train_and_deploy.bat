@echo off
echo ================================================================================
echo YOLO TRAINING AND iOS DEPLOYMENT PIPELINE
echo ================================================================================
echo.
echo 🚀 This will train a YOLO model on your generated synthetic data
echo    and prepare it for iOS deployment.
echo.
echo Prerequisites:
echo   - Python with pip installed
echo   - Generated synthetic data in desk_renders/
echo   - GPU recommended (CUDA) for faster training
echo.

set /p CONTINUE="Continue with training? (y/n): "
if /i "%CONTINUE%" NEQ "y" (
    echo Training cancelled.
    pause
    exit /b 0
)

echo.
echo 📦 Installing training dependencies...
echo.

pip install ultralytics torch torchvision opencv-python PyYAML

echo.
echo 🎯 Starting YOLO training pipeline...
echo.

python training/train_yolo_model.py

echo.
echo ================================================================================
echo ✅ TRAINING AND EXPORT COMPLETE
echo ================================================================================
echo.
echo Your new model should be ready in the iOS project directory.
echo.
echo Next steps:
echo   1. Open Xcode project: yolo-ios-app/YOLOiOSApp/YOLOiOSApp.xcodeproj
echo   2. Update model name in YOLO.swift (see update_ios_model.md)
echo   3. Test on device
echo   4. Deploy to App Store
echo.
pause