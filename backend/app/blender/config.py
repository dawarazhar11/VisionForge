"""
Blender rendering configuration schemas and constants.
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field
from loguru import logger


# Default Blender executable path (can be overridden via environment variable)
DEFAULT_BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


def find_blender_executable() -> Optional[str]:
    """
    Auto-detect Blender installation path on the system.

    Searches in the following order:
    1. BLENDER_PATH environment variable
    2. PATH environment variable
    3. Common Windows installation directories
    4. Windows Registry (if on Windows)

    Returns:
        Path to blender.exe if found, None otherwise
    """
    # 1. Check BLENDER_PATH environment variable
    env_path = os.environ.get("BLENDER_PATH")
    if env_path and os.path.exists(env_path):
        logger.info(f"Found Blender via BLENDER_PATH: {env_path}")
        return env_path

    # 2. Check if blender is in PATH
    blender_in_path = shutil.which("blender")
    if blender_in_path:
        logger.info(f"Found Blender in PATH: {blender_in_path}")
        return blender_in_path

    # 3. Check common Windows installation paths
    if sys.platform == "win32":
        common_paths = [
            # Program Files locations
            r"C:\Program Files\Blender Foundation",
            r"C:\Program Files (x86)\Blender Foundation",
            # User AppData locations
            Path.home() / "AppData" / "Local" / "Programs" / "Blender Foundation",
            # Scoop installation
            Path.home() / "scoop" / "apps" / "blender",
            # Chocolatey installation
            r"C:\ProgramData\chocolatey\lib\blender\tools",
        ]

        for base_path in common_paths:
            base = Path(base_path)
            if not base.exists():
                continue

            # Search for blender.exe in subdirectories with version-aware sorting
            # Extract version numbers for proper sorting (5.0 > 4.2 > 4.0 > 3.4)
            version_dirs = list(base.glob("Blender*"))

            def extract_version(path):
                """Extract version number from 'Blender X.Y' directory name."""
                try:
                    # Extract "X.Y" from "Blender X.Y"
                    version_str = path.name.replace("Blender ", "").strip()
                    # Split into major.minor and convert to tuple of ints
                    parts = version_str.split(".")
                    return tuple(int(p) for p in parts)
                except (ValueError, AttributeError):
                    # If parsing fails, return (0,) to sort these last
                    return (0,)

            # Sort by version number in descending order (newest first)
            version_dirs_sorted = sorted(version_dirs, key=extract_version, reverse=True)

            for version_dir in version_dirs_sorted:
                blender_exe = version_dir / "blender.exe"
                if blender_exe.exists():
                    logger.info(f"Found Blender at: {blender_exe}")
                    return str(blender_exe)

        # 4. Check Windows Registry (Blender installer creates registry keys)
        try:
            import winreg

            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlenderFoundation"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\BlenderFoundation"),
            ]

            for hkey, reg_path in registry_paths:
                try:
                    with winreg.OpenKey(hkey, reg_path) as key:
                        # Enumerate subkeys (version numbers)
                        i = 0
                        while True:
                            try:
                                version_key = winreg.EnumKey(key, i)
                                with winreg.OpenKey(hkey, f"{reg_path}\\{version_key}") as version:
                                    install_path, _ = winreg.QueryValueEx(version, "InstallDir")
                                    blender_exe = Path(install_path) / "blender.exe"
                                    if blender_exe.exists():
                                        logger.info(f"Found Blender via Registry: {blender_exe}")
                                        return str(blender_exe)
                                i += 1
                            except OSError:
                                break
                except FileNotFoundError:
                    continue
        except ImportError:
            logger.debug("winreg module not available (non-Windows platform)")
        except Exception as e:
            logger.debug(f"Registry search failed: {e}")

    # Not found
    logger.warning("Blender executable not found in common locations")
    return None


def get_blender_path() -> str:
    """
    Get Blender executable path with auto-detection fallback.

    Returns:
        Path to blender.exe

    Raises:
        FileNotFoundError: If Blender cannot be found
    """
    # Try auto-detection first
    detected_path = find_blender_executable()
    if detected_path:
        return detected_path

    # Fall back to default path
    if os.path.exists(DEFAULT_BLENDER_PATH):
        logger.info(f"Using default Blender path: {DEFAULT_BLENDER_PATH}")
        return DEFAULT_BLENDER_PATH

    # Nothing found - provide helpful error message
    error_msg = (
        "Blender executable not found. Please install Blender or set the BLENDER_PATH environment variable.\n\n"
        "Download Blender: https://www.blender.org/download/\n\n"
        "Or set environment variable:\n"
        "  Windows (PowerShell): $env:BLENDER_PATH = 'C:\\Path\\To\\blender.exe'\n"
        "  Windows (CMD): set BLENDER_PATH=C:\\Path\\To\\blender.exe\n"
        "  Linux/Mac: export BLENDER_PATH=/path/to/blender\n\n"
        f"Searched locations:\n"
        f"  - BLENDER_PATH environment variable\n"
        f"  - System PATH\n"
        f"  - C:\\Program Files\\Blender Foundation\n"
        f"  - User AppData directory\n"
        f"  - Windows Registry\n"
        f"  - Default path: {DEFAULT_BLENDER_PATH}"
    )

    logger.error(error_msg)
    raise FileNotFoundError(error_msg)

# Default rendering parameters
DEFAULT_RENDER_PARAMS = {
    "num_renders": 15,
    "resolution_x": 1920,
    "resolution_y": 1080,
    "eevee_samples": 64,
    "focal_length": 50,
    "rotation_range_x": 30,
    "rotation_range_y": 5,
    "rotation_range_z": 20,
    "distance_closer": 0.10,
    "distance_farther": 0.50,
}


class BlenderRenderConfig(BaseModel):
    """Configuration for Blender rendering job."""

    num_renders: int = Field(
        default=15,
        ge=1,
        le=1000,
        description="Number of synthetic images to generate"
    )
    resolution_x: int = Field(
        default=1920,
        ge=256,
        le=4096,
        description="Output image width in pixels"
    )
    resolution_y: int = Field(
        default=1080,
        ge=256,
        le=4096,
        description="Output image height in pixels"
    )
    eevee_samples: int = Field(
        default=64,
        ge=8,
        le=256,
        description="Rendering quality (higher = better quality, slower)"
    )
    focal_length: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Camera focal length in mm"
    )
    rotation_range_x: int = Field(
        default=30,
        ge=0,
        le=90,
        description="Camera X rotation randomization in degrees"
    )
    rotation_range_y: int = Field(
        default=5,
        ge=0,
        le=90,
        description="Camera Y rotation randomization in degrees"
    )
    rotation_range_z: int = Field(
        default=20,
        ge=0,
        le=180,
        description="Camera Z rotation randomization in degrees"
    )
    distance_closer: float = Field(
        default=0.10,
        ge=0.0,
        le=0.5,
        description="Camera zoom in factor (fraction)"
    )
    distance_farther: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Camera zoom out factor (fraction)"
    )
    use_gpu: bool = Field(
        default=True,
        description="Use GPU acceleration (OptiX/CUDA)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "num_renders": 100,
                "resolution_x": 1920,
                "resolution_y": 1080,
                "eevee_samples": 64,
                "focal_length": 50,
                "rotation_range_x": 30,
                "use_gpu": True
            }
        }


class BlenderExecutionResult(BaseModel):
    """Result of Blender rendering execution."""

    success: bool = Field(..., description="Whether rendering completed successfully")
    output_dir: str = Field(..., description="Directory containing rendered images")
    images_generated: int = Field(..., description="Number of images generated")
    labels_generated: int = Field(..., description="Number of YOLO labels generated")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    blender_log: Optional[str] = Field(None, description="Blender execution log")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "output_dir": "datasets/project_uuid/render_001",
                "images_generated": 100,
                "labels_generated": 100,
                "error_message": None,
                "blender_log": "Rendering completed successfully"
            }
        }
