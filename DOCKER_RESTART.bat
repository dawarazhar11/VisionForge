@echo off
echo ========================================
echo YOLO Vision - Docker Restart
echo ========================================
echo.

echo Stopping services...
docker-compose down

echo.
echo Starting services...
docker-compose up -d

echo.
echo Waiting for services to be healthy...
timeout /t 10 /nobreak > nul

echo.
echo Service status:
docker-compose ps

echo.
echo ========================================
echo Services restarted successfully!
echo ========================================
echo.
echo Backend API:  http://localhost:8002
echo API Docs:     http://localhost:8002/docs
echo.
pause
