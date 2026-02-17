@echo off
echo ========================================
echo YOLO Vision - Podman Logs
echo ========================================
echo.
echo Showing logs for all services...
echo Press Ctrl+C to exit
echo.

REM Follow logs for all services
podman-compose logs -f
