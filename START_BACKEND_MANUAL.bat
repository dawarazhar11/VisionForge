@echo off
REM Quick Start Backend for Testing (No Containers!)
echo ========================================
echo Starting Backend Server Manually
echo ========================================
echo.

REM Step 1: Kill old backend processes on port 8002
echo [1/3] Killing old backend processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8002"') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak > nul

REM Step 2: Start PostgreSQL container (needed for database)
echo.
echo [2/3] Starting PostgreSQL container...
podman start yolo_postgres 2>nul
if errorlevel 1 (
    echo PostgreSQL container not found, starting with compose...
    cd "%~dp0"
    podman-compose up -d postgres
)
timeout /t 3 /nobreak > nul

REM Step 3: Start Redis container (needed for Celery)
echo.
echo Starting Redis container...
podman start yolo_redis 2>nul
if errorlevel 1 (
    echo Redis container not found, starting with compose...
    cd "%~dp0"
    podman-compose up -d redis
)
timeout /t 2 /nobreak > nul

REM Step 4: Start backend with venv
echo.
echo [3/3] Starting Backend API Server...
echo.
echo ========================================
echo Backend Starting with FIXED CODE!
echo ========================================
echo.
echo Access Points:
echo - API Docs: http://localhost:8002/docs
echo - Health:   http://localhost:8002/health
echo - Projects: http://localhost:8002/api/v1/projects/
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.

cd "%~dp0backend"
..\backend_venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
