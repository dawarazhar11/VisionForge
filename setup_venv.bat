@echo off
echo ================================================================================
echo SETTING UP PYTHON VIRTUAL ENVIRONMENT FOR BLENDER SCRIPTS
echo ================================================================================
echo.
echo 🐍 Creating virtual environment...
echo.

python -m venv blender_venv

echo.
echo 📦 Installing required packages...
echo.

call blender_venv\Scripts\activate.bat
pip install opencv-python numpy

echo.
echo ================================================================================
echo ✅ VIRTUAL ENVIRONMENT SETUP COMPLETE
echo ================================================================================
echo.
echo Virtual environment created: blender_venv\
echo Packages installed: opencv-python, numpy
echo.
echo The Blender script has been updated to use this environment.
echo You can now run: run_memory_safe_desk_scene.bat
echo.
pause