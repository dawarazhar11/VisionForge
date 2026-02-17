@echo off
echo ================================================================================
echo INSTALLING PACKAGES LOCALLY (NO ADMIN REQUIRED)
================================================================================
echo.
echo 📦 Installing packages to local directory: blender_packages\
echo.

mkdir blender_packages 2>nul

set BLENDER_PYTHON="C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe"

echo 🔧 Installing opencv-python and numpy...
%BLENDER_PYTHON% -m pip install opencv-python==4.10.0.84 numpy==1.24.4 --target blender_packages --upgrade

echo.
echo ================================================================================
echo ✅ LOCAL INSTALLATION COMPLETE
================================================================================
echo.
echo Packages installed to: blender_packages\
echo The script has been updated to use these packages.
echo You can now run: run_memory_safe_desk_scene.bat
echo.
pause