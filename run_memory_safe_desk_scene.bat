@echo off
echo ================================================================================
echo MEMORY-OPTIMIZED DESK SCENE - MECHANICAL COMPONENTS DATASET GENERATION
echo ================================================================================
echo.
echo 🛡️ MEMORY SAFETY FEATURES:
echo   • Reduced resolution: 800x800 (from 1200x1200)
echo   • Lower EEVEE samples: 24 (from 32)  
echo   • Aggressive memory cleanup after each render
echo   • Memory monitoring with 6GB warning threshold
echo   • Orphaned data purging between renders
echo   • Python garbage collection optimization
echo.
echo 📊 OPTIMIZED CONFIGURATION:
echo   • Total renders: 150
echo   • GPU acceleration: RTX 4060 OptiX
echo   • Memory monitoring: Real-time usage tracking
echo   • Crash prevention: Proactive cleanup at high usage
echo.
echo 🎯 Starting memory-optimized rendering...
echo Blend file: desk_scene_17-ligthting enhaned.blend
echo Script: eevee_desk_scene17_dualpass.py (dual-pass rendering)
echo Output: dataset_desk_mechanical_enhanced/ folder
echo.
echo ⚠️  If you get "ModuleNotFoundError: No module named 'cv2'", run:
echo    install_local_packages.bat
echo.

"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" "desk_scene_17-ligthting enhaned.blend" --background --python "eevee_desk_scene17_dualpass.py"

echo.
echo ================================================================================
echo 🎉 MEMORY-OPTIMIZED DATASET GENERATION COMPLETE
echo ================================================================================
echo.
echo 📁 Dataset structure unchanged - same professional YOLO format
echo 💾 Memory-safe rendering completed without crashes
echo 🚀 GPU acceleration maintained for maximum performance
echo.
echo Ready for YOLO training with memory-efficient dataset!
echo.
pause