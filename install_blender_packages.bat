@echo off
echo ================================================================================
echo INSTALLING REQUIRED PYTHON PACKAGES FOR BLENDER
echo ================================================================================
echo.
echo 📦 Installing required packages in Blender's Python environment:
echo   • opencv-python (cv2)
echo   • numpy
echo.
echo This may take a few minutes...
echo.

"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "install_blender_deps.py"

echo.
echo ================================================================================
echo 📦 PACKAGE INSTALLATION COMPLETE
echo ================================================================================
echo.
echo You can now run the dataset generation:
echo   run_memory_safe_desk_scene.bat
echo.
pause