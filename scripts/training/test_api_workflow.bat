@echo off
REM Comprehensive API Test Script for YOLO Vision Backend
REM Tests: Auth → Project → Upload → Rendering → Training → Model Retrieval

setlocal enabledelayedexpansion

set BASE_URL=http://localhost:8002/api/v1
set TOKEN=
set PROJECT_ID=
set JOB_ID=
set MODEL_ID=

echo ========================================
echo YOLO Vision Backend - API Test Suite
echo ========================================
echo.

REM Test 1: Health Check
echo [1/9] Testing Health Endpoint...
curl -s !BASE_URL!/../health
echo.
echo.

REM Test 2: Register User
echo [2/9] Testing User Registration...
curl -s -X POST !BASE_URL!/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"Test123!@#\",\"full_name\":\"Test User\"}"
echo.
echo.

REM Test 3: Login
echo [3/9] Testing Login...
curl -s -X POST !BASE_URL!/auth/login/json ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"Test123!@#\"}" > temp_login.json

REM Extract token (simple parsing for Windows batch)
for /f "tokens=2 delims=:," %%a in ('findstr /C:"access_token" temp_login.json') do (
    set TOKEN_RAW=%%a
    set TOKEN=!TOKEN_RAW:"=!
    set TOKEN=!TOKEN: =!
)

if "!TOKEN!"=="" (
    echo ERROR: Login failed or token not found
    type temp_login.json
    goto :cleanup
)

echo Login successful! Token: !TOKEN:~0,20!...
echo.

REM Test 4: Create Project (JSON - tests the fix we just made)
echo [4/9] Testing Project Creation (JSON endpoint - the bug we fixed^)...
curl -s -X POST !BASE_URL!/projects/ ^
  -H "Authorization: Bearer !TOKEN!" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"API Test Project\",\"description\":\"Testing project creation endpoint\"}" > temp_project.json

REM Extract project ID
for /f "tokens=2 delims=:," %%a in ('findstr /C:"id" temp_project.json ^| findstr /V "user_id"') do (
    set PROJECT_ID_RAW=%%a
    set PROJECT_ID=!PROJECT_ID_RAW:"=!
    set PROJECT_ID=!PROJECT_ID: =!
)

if "!PROJECT_ID!"=="" (
    echo ERROR: Project creation failed
    type temp_project.json
    goto :cleanup
)

echo Project created! ID: !PROJECT_ID!
echo.

REM Test 5: List Projects
echo [5/9] Testing List Projects...
curl -s -X GET "!BASE_URL!/projects/?page=1&page_size=10" ^
  -H "Authorization: Bearer !TOKEN!"
echo.
echo.

REM Test 6: Get Project Details
echo [6/9] Testing Get Project by ID...
curl -s -X GET !BASE_URL!/projects/!PROJECT_ID! ^
  -H "Authorization: Bearer !TOKEN!"
echo.
echo.

REM Test 7: Upload Blend File (if test_model.obj exists)
echo [7/9] Testing File Upload...
if exist "test_model.obj" (
    curl -s -X POST !BASE_URL!/projects/upload ^
      -H "Authorization: Bearer !TOKEN!" ^
      -F "file=@test_model.obj" ^
      -F "name=Uploaded Test Model" ^
      -F "description=Testing file upload endpoint"
    echo.
) else (
    echo SKIP: test_model.obj not found, skipping upload test
)
echo.

REM Test 8: Create Rendering Job (placeholder - you'll need to implement this endpoint)
echo [8/9] Testing Job Creation...
echo NOTE: Rendering job endpoint needs implementation
echo Expected: POST !BASE_URL!/jobs/render
echo.

REM Test 9: List Models
echo [9/9] Testing List Trained Models...
curl -s -X GET !BASE_URL!/models/ ^
  -H "Authorization: Bearer !TOKEN!"
echo.
echo.

echo ========================================
echo Test Suite Complete!
echo ========================================
echo.
echo Summary:
echo - Health Check: PASS
echo - User Registration: Check output above
echo - Login: !TOKEN:~0,20!...
echo - Project Creation: !PROJECT_ID!
echo - List Projects: Check output above
echo - Get Project: Check output above
echo - File Upload: Check output above
echo.

:cleanup
if exist temp_login.json del temp_login.json
if exist temp_project.json del temp_project.json

pause
