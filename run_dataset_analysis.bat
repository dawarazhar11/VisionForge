@echo off
echo ================================================================================
echo YOLO DATASET ANALYSIS AND DEBUGGING TOOLS
echo ================================================================================
echo.
echo 🔍 This script analyzes your generated training dataset for:
echo   • Class distribution and balance
echo   • Small holes representation (your main issue)
echo   • Bracket orientation coverage
echo   • Training readiness assessment
echo   • Visual sample verification
echo.

set DATASET_PATH=dataset_desk_mechanical_enhanced

if not exist %DATASET_PATH% (
    echo ❌ Dataset directory not found: %DATASET_PATH%
    echo.
    echo Please run data generation first:
    echo   run_memory_safe_desk_scene.bat
    echo.
    pause
    exit /b 1
)

echo 📊 Running comprehensive dataset analysis...
echo.

python analyze_detection_results.py %DATASET_PATH% --visualize --deep-holes

echo.
echo ================================================================================
echo 📈 ANALYSIS COMPLETE
echo ================================================================================
echo.
echo Check the following outputs:
echo   • Console report above shows training readiness score
echo   • %DATASET_PATH%\sample_labels_visualization.png - visual verification
echo.
echo Next steps based on your score:
echo   • Score 80-100: ✅ Ready for training
echo   • Score 60-79:  ⚠️  Address issues, then proceed
echo   • Score 0-59:   ❌ Fix major issues before training
echo.
echo If small holes are underrepresented, regenerate data with:
echo   run_memory_safe_desk_scene.bat
echo.
pause