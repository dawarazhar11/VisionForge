@echo off
echo ========================================
echo YOLO Vision - Docker Shutdown
echo ========================================
echo.

echo Stopping all Docker services...
echo.

REM Stop all services
docker-compose down

echo.
echo ========================================
echo All Docker services stopped
echo ========================================
echo.
echo To start services again, run: DOCKER_START.bat
echo To completely remove containers and volumes: DOCKER_CLEANUP.bat
echo.
pause
