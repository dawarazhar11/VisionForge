"""
Quick setup script for YOLO training environment
Checks system compatibility and installs dependencies
"""
import os
import sys
import subprocess
import platform

def check_python_version():
    """Check Python version compatibility"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} detected")
        print("⚠️  YOLO training requires Python 3.8 or higher")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_cuda():
    """Check CUDA availability for GPU acceleration"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ NVIDIA GPU detected - CUDA acceleration available")
            return True
    except FileNotFoundError:
        pass
    
    print("⚠️  No NVIDIA GPU detected - will use CPU (slower training)")
    return False

def install_dependencies():
    """Install required packages for YOLO training"""
    packages = [
        'ultralytics',
        'torch',
        'torchvision', 
        'opencv-python',
        'PyYAML',
        'matplotlib',
        'seaborn'
    ]
    
    print("\n📦 Installing training dependencies...")
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    
    return True

def verify_dataset():
    """Check if synthetic dataset exists and is properly formatted"""
    dataset_dir = "desk_renders"
    
    if not os.path.exists(dataset_dir):
        print(f"❌ Dataset directory '{dataset_dir}' not found")
        print("Run 'run_memory_safe_desk_scene.bat' first to generate data")
        return False
    
    # Count image/label pairs
    images = [f for f in os.listdir(dataset_dir) if f.endswith('.jpg') and f.startswith('render_')]
    labels = [f for f in os.listdir(dataset_dir) if f.endswith('.txt') and f.startswith('render_')]
    
    print(f"📊 Found {len(images)} images and {len(labels)} label files")
    
    if len(images) != len(labels):
        print("⚠️  Image/label count mismatch - some files may be missing")
    
    if len(images) < 10:
        print("⚠️  Very small dataset - consider generating more data")
        return False
    
    print(f"✅ Dataset looks good with {len(images)} training examples")
    return True

def main():
    print("="*60)
    print("🚀 YOLO TRAINING ENVIRONMENT SETUP")
    print("="*60)
    
    # System checks
    print("\n🔍 System Compatibility Check:")
    python_ok = check_python_version()
    cuda_available = check_cuda()
    
    if not python_ok:
        print("\n❌ Setup failed - Python version incompatible")
        return False
    
    # Dataset check
    print("\n📂 Dataset Verification:")
    dataset_ok = verify_dataset()
    
    if not dataset_ok:
        print("\n⚠️  Dataset issues detected - fix before training")
    
    # Install dependencies
    deps_ok = install_dependencies()
    
    if not deps_ok:
        print("\n❌ Setup failed - dependency installation error")
        return False
    
    # Final summary
    print("\n" + "="*60)
    print("✅ SETUP COMPLETE!")
    print("="*60)
    print(f"🐍 Python: Compatible")
    print(f"🎮 GPU: {'Available' if cuda_available else 'Not available (CPU only)'}")
    print(f"📊 Dataset: {'Ready' if dataset_ok else 'Needs attention'}")
    print(f"📦 Dependencies: Installed")
    
    if dataset_ok:
        print(f"\n🎯 Ready to train! Run:")
        print(f"   train_and_deploy.bat")
        print(f"   -- OR --")
        print(f"   python train_yolo_model.py")
    else:
        print(f"\n⚠️  Generate synthetic data first:")
        print(f"   run_memory_safe_desk_scene.bat")
    
    return True

if __name__ == "__main__":
    main()