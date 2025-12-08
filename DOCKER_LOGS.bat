@echo off
echo ========================================
echo YOLO Vision - Docker Logs
echo ========================================
echo.
echo Showing logs for all services...
echo Press Ctrl+C to exit
echo.

REM Follow logs for all services
docker-compose logs -f
