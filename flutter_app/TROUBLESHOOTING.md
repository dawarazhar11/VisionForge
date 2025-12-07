# Troubleshooting Guide

## "Format Error / Unexpected Character" When Creating Project

### Problem
You see an error like "format error unexpected character" when trying to create a new project.

### Causes
1. **Backend not running** - The API server isn't started
2. **Authentication issue** - Not logged in or token expired
3. **API endpoint mismatch** - Flutter app and backend using different API paths

### Solutions

#### Solution 1: Verify Backend is Running
```batch
# Check if backend is running on port 8002
netstat -ano | findstr ":8002"
```

If no output, start the backend:
```batch
cd "H:\Yolo Computer Vision\Baseline"
START_APP.bat
```

Or manually:
```batch
cd "H:\Yolo Computer Vision\Baseline\backend"
..\backend_venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Verify it's working:
- Open browser: http://localhost:8002
- You should see: `{"name":"YOLO Assembly Vision API","version":"0.1.0","status":"running","docs":"/docs"}`

#### Solution 2: Check API Documentation
Visit http://localhost:8002/docs to see available endpoints:
- Verify `/api/auth/register` exists
- Verify `/api/auth/login` exists
- Verify `/api/projects/` exists

#### Solution 3: Run App in Development Mode (See Detailed Errors)
Instead of the release .exe, run:
```batch
cd "H:\Yolo Computer Vision\Baseline\flutter_app"
flutter run -d windows
```

This will show detailed error messages in the console including:
- `Create project response status: 404` (endpoint not found)
- `Create project response body: {"detail":"Not Found"}` (endpoint missing)
- `Create project error: Exception: Failed to create project` (actual error)

#### Solution 4: Check Authentication
Make sure you're logged in:
1. Register a new account first
2. Login with valid credentials
3. Token is automatically saved
4. Try creating project again

#### Solution 5: Verify API Configuration
Check the API base URL in `lib/utils/api_config.dart`:
```dart
class ApiConfig {
  static const String baseUrl = 'http://localhost:8002';
  // ...
}
```

Change if your backend runs on a different port.

## Other Common Issues

### "Unable to connect to server"

**Problem:** Can't reach the backend API

**Solutions:**
1. Start backend: `START_APP.bat`
2. Check firewall isn't blocking port 8002
3. Verify API URL in `api_config.dart`

### "Authentication failed"

**Problem:** Login doesn't work

**Solutions:**
1. Make sure you've registered an account first
2. Check email and password are correct
3. Restart backend if database is corrupted
4. Try registering with a different email

### "No camera detected"

**Problem:** Camera screen is blank

**Solutions:**
- **Windows:** Settings → Privacy → Camera → Allow desktop apps
- **Android:** App Settings → Permissions → Camera → Allow
- Connect USB webcam if no built-in camera
- Grant camera permission when prompted

### App Crashes on Startup

**Problem:** App closes immediately

**Solutions:**
1. **Check backend is running**
2. **Run in development mode to see errors:**
   ```batch
   cd flutter_app
   flutter run -d windows
   ```
3. Check console for error details
4. Common cause: Backend not running

## Development Mode vs Release Mode

### Release Mode (the .exe file)
- **Location:** `build\windows\x64\runner\Release\yolo_vision_app.exe`
- **Pros:** Faster, standalone executable
- **Cons:** No error messages, harder to debug

### Development Mode (flutter run)
- **Command:** `flutter run -d windows`
- **Pros:**
  - Hot reload (instant code updates)
  - Detailed error messages in console
  - Easy debugging
- **Cons:** Slower, requires Flutter SDK

**Recommended for troubleshooting:** Always use development mode first!

## How to Debug

### Step 1: Run in Development Mode
```batch
cd "H:\Yolo Computer Vision\Baseline\flutter_app"
flutter run -d windows
```

### Step 2: Check Console Output
Look for error messages like:
- `Create project response status: 404`
- `Connection refused`
- `FormatException`
- Stack traces

### Step 3: Test Backend Directly
```batch
# Test if backend responds
curl http://localhost:8002

# Test projects endpoint (requires authentication)
curl http://localhost:8002/api/projects/
```

### Step 4: Check Backend Logs
If backend is running in a terminal, check for:
- Python exceptions
- Database errors
- CORS errors

## API Endpoint Reference

**Backend should provide these endpoints:**

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/` | GET | API info | No |
| `/docs` | GET | Swagger UI | No |
| `/api/auth/register` | POST | Create account | No |
| `/api/auth/login` | POST | Login | No |
| `/api/auth/refresh` | POST | Refresh token | Yes |
| `/api/projects/` | GET | List projects | Yes |
| `/api/projects/` | POST | Create project | Yes |
| `/api/projects/{id}` | GET | Get project | Yes |
| `/api/training/jobs` | GET | List jobs | Yes |
| `/api/training/jobs` | POST | Create job | Yes |

## Quick Test Procedure

To verify everything works:

1. **Start backend:**
   ```batch
   START_APP.bat
   ```

2. **Verify backend:**
   - Open http://localhost:8002 in browser
   - Should see API info JSON

3. **Run Flutter app in dev mode:**
   ```batch
   cd flutter_app
   flutter run -d windows
   ```

4. **Try registration:**
   - Click "Register"
   - Fill in details
   - Watch console for errors

5. **Try login:**
   - Enter credentials
   - Watch console for response

6. **Try create project:**
   - Click "+"
   - Enter project name
   - Watch console for:
     - `Create project response status: 201` (success)
     - `Create project response body: {...}` (project data)

## If Problem Persists

### Collect Debug Information:
1. Backend response status code
2. Backend response body
3. Error message from Flutter console
4. Backend terminal output

### Common Fixes:
1. **Restart everything:**
   ```batch
   STOP_APP.bat
   START_APP.bat
   ```

2. **Rebuild Flutter app:**
   ```batch
   cd flutter_app
   flutter clean
   flutter pub get
   flutter build windows --release
   ```

3. **Reset database (if corrupted):**
   ```batch
   cd backend
   del yolo_vision.db
   ..\backend_venv\Scripts\alembic.exe upgrade head
   ```

## Need More Help?

Check these files:
- `QUICK_START_GUIDE.md` - Complete usage guide
- `backend/API_DOCUMENTATION.md` - Backend API reference
- `backend/README.md` - Backend setup guide

Or run the app in development mode and check console output for specific errors.
