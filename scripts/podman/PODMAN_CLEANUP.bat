@echo off
echo ========================================
echo YOLO Vision - Podman Cleanup
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
podman-compose down -v

echo.
echo Removing Podman images...
podman-compose down --rmi all

echo.
echo Pruning unused containers and volumes...
podman system prune -af --volumes

echo.
echo ========================================
echo Cleanup complete!
echo ========================================
echo.
echo All containers, volumes, and images removed.
echo To start fresh, run: PODMAN_START.bat
echo.
pause
