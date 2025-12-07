@echo off
echo ========================================
echo YOLO Vision App - Shutdown
echo ========================================
echo.

echo Stopping Flutter Windows App...
taskkill /F /IM yolo_vision_app.exe /T 2>nul
if %errorlevel% == 0 (
    echo ✓ Flutter app stopped
) else (
    echo ✗ Flutter app not running
)

echo.
echo Stopping Backend API (Python/Uvicorn)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8002" ^| findstr "LISTENING"') do (
    echo Killing process %%a on port 8002...
    taskkill /F /PID %%a 2>nul
)

echo.
echo ========================================
echo All services stopped
echo ========================================
pause
