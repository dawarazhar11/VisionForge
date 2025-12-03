@echo off
echo ================================================================================
echo INSTALLING PACKAGES TO BLENDER'S PYTHON (REQUIRES ADMIN RIGHTS)
================================================================================ 
echo.
echo This script needs to run as Administrator to write to Program Files.
echo Right-click this file and select "Run as administrator"
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: This script must be run as Administrator
    echo.
    echo Right-click on "install_blender_admin.bat" and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo ✅ Running with Administrator privileges
echo.
echo 🔧 Installing opencv-python and numpy to Blender's Python...
echo.

set BLENDER_PYTHON="C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe"
set BLENDER_SITE_PACKAGES="C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\Lib\site-packages"

%BLENDER_PYTHON% -m pip install opencv-python numpy --target %BLENDER_SITE_PACKAGES% --upgrade

echo.
echo ================================================================================
echo ✅ INSTALLATION COMPLETE
echo ================================================================================
echo.
echo Packages installed to Blender's Python environment.
echo You can now run: run_memory_safe_desk_scene.bat
echo.
pause