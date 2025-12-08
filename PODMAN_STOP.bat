@echo off
echo ========================================
echo YOLO Vision - Podman Shutdown
echo ========================================
echo.

echo Stopping all services...
echo.

REM Stop all services
podman-compose down

echo.
echo ========================================
echo All services stopped
echo ========================================
echo.
echo To start services again, run: PODMAN_START.bat
echo To completely remove containers: PODMAN_CLEANUP.bat
echo.
pause
