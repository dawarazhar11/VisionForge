# render_script.py
# ============================================================================
# API-Adapted Blender Rendering Script for Synthetic Data Generation
# Purpose: Dual-pass rendering with environment variable configuration
# ============================================================================

import sys
import os

# Add local packages directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_packages = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))), "blender_packages")
if os.path.exists(workspace_packages):
    sys.path.insert(0, workspace_packages)
    print(f"✅ Using local packages: {workspace_packages}")

import bpy, io, contextlib, time, math, random

# Debug Python environment
print(f"🐍 Python executable: {sys.executable}")
print(f"🔍 Python version: {sys.version}")

# Check for required packages
try:
    import cv2
    import numpy as np
    print("✅ All required packages are available")
    print(f"   OpenCV version: {cv2.__version__}")
    print(f"   NumPy version: {np.__version__}")
except ImportError as e:
    print("=" * 80)
    print("❌ MISSING REQUIRED PACKAGES")
    print("=" * 80)
    print(f"Error: {e}")
    print("To fix this, ensure opencv-python and numpy are installed in Blender's Python")
    print("=" * 80)
    raise SystemExit("Cannot proceed without required packages")

# =========================== CONFIG (From Environment) ==============================
NUM_RENDERS = int(os.environ.get("BLENDER_NUM_RENDERS", "15"))
RESOLUTION_X = int(os.environ.get("BLENDER_RESOLUTION_X", "1920"))
RESOLUTION_Y = int(os.environ.get("BLENDER_RESOLUTION_Y", "1080"))
EEVEE_SAMPLES = int(os.environ.get("BLENDER_EEVEE_SAMPLES", "64"))
OUTPUT_DIR_NAME = os.environ.get("BLENDER_OUTPUT_DIR", "desk_renders")

# Camera randomization settings
FOCAL_LENGTH = int(os.environ.get("BLENDER_FOCAL_LENGTH", "50"))
ROTATION_RANGE_X = int(os.environ.get("BLENDER_ROTATION_X", "30"))
ROTATION_RANGE_Y = int(os.environ.get("BLENDER_ROTATION_Y", "5"))
ROTATION_RANGE_Z = int(os.environ.get("BLENDER_ROTATION_Z", "20"))
DISTANCE_CLOSER = float(os.environ.get("BLENDER_DISTANCE_CLOSER", "0.10"))
DISTANCE_FARTHER = float(os.environ.get("BLENDER_DISTANCE_FARTHER", "0.50"))

print("=" * 80)
print("🎬 RENDER CONFIGURATION")
print("=" * 80)
print(f"   Images to render: {NUM_RENDERS}")
print(f"   Resolution: {RESOLUTION_X}x{RESOLUTION_Y}")
print(f"   EEVEE samples: {EEVEE_SAMPLES}")
print(f"   Output directory: {OUTPUT_DIR_NAME}")
print(f"   Camera focal length: {FOCAL_LENGTH}mm")
print(f"   Camera randomization: ±{ROTATION_RANGE_X}°/±{ROTATION_RANGE_Y}°/±{ROTATION_RANGE_Z}°")
print(f"   Distance range: -{DISTANCE_CLOSER*100:.0f}% to +{DISTANCE_FARTHER*100:.0f}%")
print("=" * 80)

# Classes for mechanical components (YOLO seg)
CLASSES = {
    0: "small_screw",
    1: "small_hole",
    2: "large_screw",
    3: "large_hole",
    4: "bracket_A",
    5: "bracket_B",
    6: "surface"
}

# Pass index mapping for object identification in masks
PASS_INDEX_MAP = {
    # Small screws: 1-11
    'screw_01': 1, 'screw_02': 2, 'screw_03': 3, 'screw_04': 4, 'screw_05': 5,
    'screw_06': 6, 'screw_07': 7, 'screw_08': 8, 'screw_09': 9, 'screw_10': 10, 'screw_11': 11,
    # Small patches: 12-22
    'screw_01_patch': 12, 'screw_02_patch': 13, 'screw_03_patch': 14, 'screw_04_patch': 15,
    'screw_05_patch': 16, 'screw_06_patch': 17, 'screw_07_patch': 18, 'screw_08_patch': 19,
    'screw_09_patch': 20, 'screw_10_patch': 21, 'screw_11_patch': 22,
    # Large screws and patches
    'screw_left': 23, 'screw_left_patch': 24, 'screw_right': 25, 'screw_right_patch': 26,
    # Large holes
    'large_screw_hole_left': 27, 'large_screw_hole_right': 28,
    # Brackets
    'bracket_A1': 29, 'bracket_A1_hole': 30, 'bracket_A2': 31, 'bracket_A2_hole': 32,
    'bracket_B1': 33, 'bracket_B1_hole': 34, 'bracket_B2': 35, 'bracket_B2_hole': 36,
    # Main body and extras
    'empty_surface': 38, 'rubber_band': 39
}

OBJ_TO_CLASS = {
    # Small screws (class 0: "small_screw")
    "screw_01": 0, "screw_02": 0, "screw_03": 0, "screw_04": 0, "screw_05": 0,
    "screw_06": 0, "screw_07": 0, "screw_08": 0, "screw_09": 0, "screw_10": 0,
    "screw_11": 0,

    # Large screws (class 2: "large_screw")
    "screw_left": 2, "screw_right": 2,

    # Small holes (class 1: "small_hole")
    "screw_01_patch": 1, "screw_02_patch": 1, "screw_03_patch": 1, "screw_04_patch": 1,
    "screw_05_patch": 1, "screw_06_patch": 1, "screw_07_patch": 1, "screw_08_patch": 1,
    "screw_09_patch": 1, "screw_10_patch": 1, "screw_11_patch": 1,

    # Large holes (class 3: "large_hole")
    "large_screw_hole_left": 3, "large_screw_hole_right": 3,
    "screw_left_patch": 3, "screw_right_patch": 3,

    # Bracket A (class 4: "bracket_A")
    "bracket_A1": 4, "bracket_A2": 4,
    "bracket_A1_hole": 1, "bracket_A2_hole": 1,

    # Bracket B (class 5: "bracket_B")
    "bracket_B1": 5, "bracket_B2": 5,
    "bracket_B1_hole": 1, "bracket_B2_hole": 1,

    # Surface elements (class 6: "surface")
    "main_body": 6,
    "empty_surface": 6,
    "dead_patch": 6, "dead_patch.001": 6, "dead_patch.002": 6, "dead_patch.003": 6,
    "dead_patch.004": 6, "dead_patch.005": 6, "dead_patch.006": 6,
    "rubber_band": 6,
}

# Polygon extraction
THRESH_FOR_MASK = 1
POLYGON_APPROX_EPS = 0.01

# ====================== EEVEE OPTIMIZATION ========================
def setup_optimized_eevee():
    """Configure EEVEE Next for fast, stable output."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    eevee = scene.eevee
    try:
        eevee.taa_render_samples = EEVEE_SAMPLES
        eevee.taa_samples = 8
        if hasattr(eevee, 'use_ssr'): eevee.use_ssr = False
        if hasattr(eevee, 'use_ssr_refraction'): eevee.use_ssr_refraction = False
        if hasattr(eevee, 'use_volumetric_shadows'): eevee.use_volumetric_shadows = False
        if hasattr(eevee, 'use_bloom'): eevee.use_bloom = False
        if hasattr(eevee, 'use_motion_blur'): eevee.use_motion_blur = False
        if hasattr(eevee, 'use_soft_shadows'): eevee.use_soft_shadows = True
        if hasattr(eevee, 'shadow_cube_size'): eevee.shadow_cube_size = '512'
        if hasattr(eevee, 'shadow_cascade_size'): eevee.shadow_cascade_size = '1024'
    except Exception as e:
        print(f"⚠️  EEVEE settings warning: {e}")
    print(f"✅ OPTIMIZED EEVEE: {EEVEE_SAMPLES} samples")

# NOTE: The rest of the script functions (randomize_camera, randomize_scene_objects, etc.)
# are imported from the original eevee_desk_scene17_dualpass.py
# For the full implementation, copy all functions from the original script

print("✅ Blender rendering script loaded successfully")
print(f"📝 Progress will be reported as: 'Rendering image X/{NUM_RENDERS}'")
