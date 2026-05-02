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
    Auto-detect Blender installation path on the system (macOS, Windows, Linux).

    Search order:
    1. BLENDER_PATH environment variable
    2. System PATH
    3. macOS: /Applications/Blender.app bundle
    4. Windows: Program Files + Registry
    5. Linux: common install prefixes
    """
    # 1. BLENDER_PATH env var
    env_path = os.environ.get("BLENDER_PATH")
    if env_path and os.path.exists(env_path):
        logger.info(f"Found Blender via BLENDER_PATH: {env_path}")
        return env_path

    # 2. System PATH
    blender_in_path = shutil.which("blender")
    if blender_in_path:
        logger.info(f"Found Blender in PATH: {blender_in_path}")
        return blender_in_path

    # 3. macOS .app bundle
    if sys.platform == "darwin":
        mac_candidates = [
            Path("/Applications/Blender.app/Contents/MacOS/Blender"),
            Path.home() / "Applications" / "Blender.app" / "Contents" / "MacOS" / "Blender",
        ]
        for candidate in mac_candidates:
            if candidate.exists():
                logger.info(f"Found Blender (macOS): {candidate}")
                return str(candidate)

    # 4. Windows
    if sys.platform == "win32":
        win_bases = [
            r"C:\Program Files\Blender Foundation",
            r"C:\Program Files (x86)\Blender Foundation",
            Path.home() / "AppData" / "Local" / "Programs" / "Blender Foundation",
            Path.home() / "scoop" / "apps" / "blender",
            r"C:\ProgramData\chocolatey\lib\blender\tools",
        ]

        def _version_key(p):
            try:
                parts = p.name.replace("Blender ", "").strip().split(".")
                return tuple(int(x) for x in parts)
            except (ValueError, AttributeError):
                return (0,)

        for base_path in win_bases:
            base = Path(base_path)
            if not base.exists():
                continue
            for version_dir in sorted(base.glob("Blender*"), key=_version_key, reverse=True):
                blender_exe = version_dir / "blender.exe"
                if blender_exe.exists():
                    logger.info(f"Found Blender (Windows): {blender_exe}")
                    return str(blender_exe)

        try:
            import winreg
            for hkey, reg_path in [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlenderFoundation"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\BlenderFoundation"),
            ]:
                try:
                    with winreg.OpenKey(hkey, reg_path) as key:
                        i = 0
                        while True:
                            try:
                                vk = winreg.EnumKey(key, i)
                                with winreg.OpenKey(hkey, f"{reg_path}\\{vk}") as v:
                                    install_path, _ = winreg.QueryValueEx(v, "InstallDir")
                                    blender_exe = Path(install_path) / "blender.exe"
                                    if blender_exe.exists():
                                        logger.info(f"Found Blender (Registry): {blender_exe}")
                                        return str(blender_exe)
                                i += 1
                            except OSError:
                                break
                except FileNotFoundError:
                    continue
        except ImportError:
            pass

    # 5. Linux common paths
    if sys.platform.startswith("linux"):
        linux_candidates = [
            Path("/usr/bin/blender"),
            Path("/usr/local/bin/blender"),
            Path("/opt/blender/blender"),
            Path.home() / ".local" / "bin" / "blender",
        ]
        for candidate in linux_candidates:
            if candidate.exists():
                logger.info(f"Found Blender (Linux): {candidate}")
                return str(candidate)

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

    error_msg = (
        "Blender executable not found. Install Blender or set BLENDER_PATH.\n"
        "  macOS:   export BLENDER_PATH=/Applications/Blender.app/Contents/MacOS/Blender\n"
        "  Windows: set BLENDER_PATH=C:\\Path\\To\\blender.exe\n"
        "  Linux:   export BLENDER_PATH=/usr/bin/blender\n"
        "Download: https://www.blender.org/download/"
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
