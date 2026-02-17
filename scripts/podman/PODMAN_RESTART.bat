@echo off
echo ========================================
echo YOLO Vision - Podman Restart
echo ========================================
echo.

echo Stopping services...
podman-compose down

echo.
echo Starting services...
podman-compose up -d

echo.
echo Waiting for services to be healthy...
timeout /t 10 /nobreak > nul

echo.
echo Service status:
podman-compose ps

echo.
echo ========================================
echo Services restarted successfully!
echo ========================================
echo.
echo Portainer UI:  http://localhost:9000
echo Backend API:   http://localhost:8002
echo API Docs:      http://localhost:8002/docs
echo.
pause
