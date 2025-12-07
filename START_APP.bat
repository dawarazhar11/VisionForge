@echo off
echo ========================================
echo YOLO Vision App - Complete Startup
echo ========================================
echo.

REM Start Backend API
echo [1/2] Starting Backend API...
cd /d "%~dp0backend"
start "YOLO Backend API" cmd /k "..\backend_venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8002

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 3 /nobreak > nul

REM Open API docs in browser
echo Opening API documentation...
start http://localhost:8002/docs

REM Start Flutter Windows App
echo.
echo [2/2] Starting Flutter Windows App...
cd /d "%~dp0flutter_app"
start "YOLO Vision App" "build\windows\x64\runner\Release\yolo_vision_app.exe"

echo.
echo ========================================
echo Both apps started successfully!
echo ========================================
echo.
echo Backend API: http://localhost:8002/docs
echo Windows App: Should open automatically
echo.
echo Press any key to close this window...
echo (Backend and app will keep running)
pause > nul
