@echo off
echo ========================================
echo Podman Installation for Windows
echo ========================================
echo.

echo This script will guide you through installing Podman on Windows.
echo.

echo Step 1: Download Podman for Windows
echo ----------------------------------------
echo Opening Podman download page...
timeout /t 2 /nobreak > nul
start https://github.com/containers/podman/releases

echo.
echo Download the latest Podman Windows installer (.exe)
echo Install it with default settings
echo.
pause

echo.
echo Step 2: Install podman-compose
echo ----------------------------------------
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Installing podman-compose...
pip install podman-compose

echo.
echo Step 3: Initialize Podman Machine
echo ----------------------------------------
echo.

echo Initializing Podman machine...
podman machine init

echo.
echo Starting Podman machine...
podman machine start

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Verify installation:
podman --version
podman-compose --version

echo.
echo Next steps:
echo 1. Run PODMAN_START.bat to start all services
echo 2. Access Portainer at http://localhost:9000
echo.
pause
