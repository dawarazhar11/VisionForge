@echo off
echo ========================================
echo YOLO Vision - Docker Startup
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting all Docker services...
echo.

REM Start all services with docker-compose
docker-compose up -d

echo.
echo ========================================
echo Waiting for services to be healthy...
echo ========================================
echo.

REM Wait for services to be ready
timeout /t 10 /nobreak > nul

echo Checking service status...
docker-compose ps

echo.
echo ========================================
echo Services Started Successfully!
echo ========================================
echo.
echo Portainer UI:  http://localhost:9000
echo Backend API:   http://localhost:8002
echo API Docs:      http://localhost:8002/docs
echo PostgreSQL:    localhost:5433
echo Redis:         localhost:6379
echo.
echo Containers will restart automatically on system boot!
echo To stop services, run: DOCKER_STOP.bat
echo.

REM Open Portainer and API docs in browser
echo Opening Portainer UI and API documentation...
timeout /t 2 /nobreak > nul
start http://localhost:9000
timeout /t 1 /nobreak > nul
start http://localhost:8002/docs

echo.
echo Press any key to close this window...
echo (Services will keep running in background)
pause > nul
