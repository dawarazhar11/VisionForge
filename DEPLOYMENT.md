# Deployment Guide

This guide provides instructions for deploying the YOLO Computer Vision Baseline application on any platform with automatic dependency management.

## Quick Start

### Windows

1. **Run the automated setup script:**
   ```batch
   cd backend
   setup_deployment.bat
   ```

2. **Or use the Python script:**
   ```batch
   cd backend
   python setup_deployment.py
   ```

### Linux/macOS

```bash
cd backend
python3 setup_deployment.py
```

## Manual Setup

If automatic setup fails, follow these manual steps:

### 1. Create Virtual Environment

```bash
# Windows
python -m venv backend_venv

# Linux/macOS
python3 -m venv backend_venv
```

### 2. Activate Virtual Environment

```bash
# Windows
backend_venv\Scripts\activate

# Linux/macOS
source backend_venv/bin/activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the `backend` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/yolo_cv
DATABASE_TEST_URL=postgresql://user:password@localhost:5432/yolo_cv_test

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Blender
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe

# API
API_V1_STR=/api/v1
PROJECT_NAME=YOLO Computer Vision Baseline
```

### 5. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

### 6. Start Services

**Terminal 1 - API Server:**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
celery -A app.celery_app worker --loglevel=info --pool=solo
```

## Dependencies

### Core Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy** - Database ORM
- **Celery** - Task queue
- **Redis** - Message broker
- **PostgreSQL** - Database

### Training Dependencies

- **ultralytics** - YOLO training framework
- **torch** - PyTorch deep learning
- **torchvision** - Computer vision utilities
- **opencv-python** - Image processing
- **numpy, scipy, matplotlib** - Scientific computing

### Rendering Dependencies

- **Blender 5.0+** - 3D rendering engine
- **opencv-python** - Image processing for labels

## Platform-Specific Notes

### Windows

- Requires **Python 3.11+**
- Install **PostgreSQL** and **Redis** separately
- Blender path typically: `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`
- Use `setup_deployment.bat` for easy setup

### Linux

- Install system dependencies:
  ```bash
  sudo apt-get update
  sudo apt-get install python3-dev python3-pip postgresql redis-server
  ```
- Blender path typically: `/usr/bin/blender`

### macOS

- Install Homebrew dependencies:
  ```bash
  brew install python postgresql redis
  brew install --cask blender
  ```
- Blender path typically: `/Applications/Blender.app/Contents/MacOS/Blender`

## Docker Deployment (Coming Soon)

Future releases will include Docker compose files for one-command deployment:

```bash
docker-compose up -d
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError` for training dependencies:

```bash
cd backend
pip install -r requirements.txt --force-reinstall
```

### Celery Not Starting

Ensure Redis is running:

```bash
# Windows
redis-server

# Linux/macOS
sudo systemctl start redis
```

### Database Connection Errors

Check PostgreSQL is running and credentials are correct in `.env` file.

###GPU Acceleration

**Default**: The system uses CPU training for maximum compatibility across platforms.

**IMPORTANT - Python Version Requirement for GPU Training**:
- **PyTorch with CUDA requires Python 3.8 - 3.12**
- **Python 3.13+ is NOT supported yet** for GPU training
- If your current venv uses Python 3.13+, you must recreate it with Python 3.11 or 3.12

**To enable GPU training** (if you have an NVIDIA GPU):

0. **Check Python Version**:
   ```bash
   python --version
   # If Python 3.13 or higher, recreate venv with Python 3.11/3.12:
   # py -3.11 -m venv backend_venv  # Windows
   # python3.11 -m venv backend_venv  # Linux/macOS
   ```

1. **Install CUDA Toolkit** from NVIDIA (CUDA 11.8 or 12.1)

2. **Uninstall CPU-only PyTorch**:
   ```bash
   cd backend
   pip uninstall torch torchvision
   ```

3. **Install PyTorch with CUDA**:
   ```bash
   # For CUDA 11.8
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

   # For CUDA 12.1
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

4. **Verify CUDA is available**:
   ```bash
   python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
   ```

5. **Change training device** in `backend/app/training/config.py`:
   ```python
   # Line 181: Change from "cpu" to "0" for GPU
   device: str = Field(default="0", description="Device(s) to use")
   ```

**Benefits of GPU training**:
- 10-50x faster training speed
- Can train larger models
- Handle bigger batch sizes

## Verification

After deployment, verify all components:

```bash
# Test API
curl http://localhost:8002/api/v1/health

# Test Celery
cd backend
python -c "from app.celery_app import celery_app; print(celery_app.control.inspect().active())"

# Test imports
python -c "import ultralytics; import torch; import cv2; print('All dependencies OK')"
```

## Production Recommendations

1. **Use a process manager** like systemd, supervisor, or PM2
2. **Set up NGINX** as a reverse proxy
3. **Enable HTTPS** with Let's Encrypt
4. **Configure firewall** rules
5. **Set up monitoring** with Prometheus/Grafana
6. **Regular backups** of database and models
7. **Log rotation** for application logs

## Support

For issues or questions:
- Check `backend/logs/` directory
- Review `test_e2e_pipeline.py` for examples
- Consult `CLAUDE.md` for development guidelines
