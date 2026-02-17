@echo off
echo ========================================
echo YOLO Vision - Docker Cleanup
echo ========================================
echo.
echo WARNING: This will remove all containers, volumes, and data!
echo.
set /p confirm="Are you sure? (yes/no): "

if /i not "%confirm%"=="yes" (
    echo Cleanup cancelled.
    pause
    exit /b 0
)

echo.
echo Stopping and removing all services...
docker-compose down -v

echo.
echo Removing Docker images...
docker-compose down --rmi all

echo.
echo ========================================
echo Cleanup complete!
echo ========================================
echo.
echo All containers, volumes, and images removed.
echo To start fresh, run: DOCKER_START.bat
echo.
pause
