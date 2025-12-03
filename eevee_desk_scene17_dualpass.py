# eevee_desk_scene17_dualpass.py
# ============================================================================
# Baseline: eevee_simple_dualpass_debug.py
# Purpose : Dual-pass rendering for desk_scene_17 with mechanical components
# Author  : Adapted for desk scene with screws, holes, and brackets
# ============================================================================

import sys
import os

# Add local packages directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
local_packages = os.path.join(script_dir, "blender_packages")
if os.path.exists(local_packages):
    sys.path.insert(0, local_packages)
    print(f"✅ Using local packages: {local_packages}")

import bpy, io, contextlib, time, math, random

# Debug Python environment
print(f"🐍 Python executable: {sys.executable}")
print(f"🔍 Python version: {sys.version}")
print(f"📁 Python path (first 3 entries):")
for i, path in enumerate(sys.path[:3]):
    print(f"   {i+1}. {path}")
print()

# Check for required packages
try:
    import cv2
    import numpy as np
    print("✅ All required packages are available")
    print(f"   OpenCV version: {cv2.__version__}")
    print(f"   NumPy version: {np.__version__}")
    print()
except ImportError as e:
    print("=" * 80)
    print("❌ MISSING REQUIRED PACKAGES")
    print("=" * 80)
    print(f"Error: {e}")
    print()
    print("Python is looking in these locations:")
    for i, path in enumerate(sys.path):
        if "site-packages" in path:
            print(f"   {path}")
    print()
    print("To fix this, run the following batch file FIRST:")
    print("   install_local_packages.bat")
    print()
    print("This will install packages directly into Blender's Python environment.")
    print("=" * 80)
    raise SystemExit("Cannot proceed without required packages")

# =========================== CONFIG (DESK SCENE) ==============================
NUM_RENDERS = 150           # render multiple mechanical components
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
EEVEE_SAMPLES = 64
OUTPUT_DIR_NAME = "desk_renders"

# Camera randomization settings
FOCAL_LENGTH = 50
ROTATION_RANGE_X = 30      # degrees
ROTATION_RANGE_Y = 5       # degrees  
ROTATION_RANGE_Z = 20      # degrees
DISTANCE_CLOSER = 0.10     # scale factor for closer  
DISTANCE_FARTHER = 0.50    # scale factor for farther (more zoomed out)

# Classes for mechanical components (YOLO seg)
CLASSES = {
    0: "small_screw",     # Small screws (screw_01 to screw_11)
    1: "small_hole",      # Small screw holes (patches show where screws go)
    2: "large_screw",     # Large screws (left and right)
    3: "large_hole",      # Large screw holes
    4: "bracket_A",       # Keyhole bracket type A
    5: "bracket_B",       # Keyhole bracket type B
    6: "surface"          # Empty surface or main body
}

# Object to class mapping for desk_scene_17
# Pass index mapping for object identification in masks
PASS_INDEX_MAP = {
    # Small screws: 1-11
    'screw_01': 1, 'screw_02': 2, 'screw_03': 3, 'screw_04': 4, 'screw_05': 5,
    'screw_06': 6, 'screw_07': 7, 'screw_08': 8, 'screw_09': 9, 'screw_10': 10, 'screw_11': 11,
    # Small patches: 12-22 (used for hole masks!)
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
    
    # Small holes (class 1: "small_hole") - patches represent where screws were removed
    "screw_01_patch": 1, "screw_02_patch": 1, "screw_03_patch": 1, "screw_04_patch": 1,
    "screw_05_patch": 1, "screw_06_patch": 1, "screw_07_patch": 1, "screw_08_patch": 1,
    "screw_09_patch": 1, "screw_10_patch": 1, "screw_11_patch": 1,
    
    # Large holes (class 3: "large_hole")
    "large_screw_hole_left": 3, "large_screw_hole_right": 3,
    "screw_left_patch": 3, "screw_right_patch": 3,
    
    # Bracket A (class 4: "bracket_A")
    "bracket_A1": 4, "bracket_A2": 4,
    "bracket_A1_hole": 1, "bracket_A2_hole": 1,  # Bracket holes are small holes
    
    # Bracket B (class 5: "bracket_B") 
    "bracket_B1": 5, "bracket_B2": 5,
    "bracket_B1_hole": 1, "bracket_B2_hole": 1,  # Bracket holes are small holes
    
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

# ====================== EEVEE OPTIMIZATION (baseline) ========================
def setup_optimized_eevee():
    """Configure EEVEE Next for fast, stable output (baseline settings)."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    eevee = scene.eevee
    try:
        eevee.taa_render_samples = EEVEE_SAMPLES
        eevee.taa_samples = 8
        # Disable costly features
        if hasattr(eevee, 'use_ssr'): eevee.use_ssr = False
        if hasattr(eevee, 'use_ssr_refraction'): eevee.use_ssr_refraction = False
        if hasattr(eevee, 'use_volumetric_shadows'): eevee.use_volumetric_shadows = False
        if hasattr(eevee, 'use_bloom'): eevee.use_bloom = False
        if hasattr(eevee, 'use_motion_blur'): eevee.use_motion_blur = False
        # Keep soft shadows; moderate shadow sizes
        if hasattr(eevee, 'use_soft_shadows'): eevee.use_soft_shadows = True
        if hasattr(eevee, 'shadow_cube_size'): eevee.shadow_cube_size = '512'
        if hasattr(eevee, 'shadow_cascade_size'): eevee.shadow_cascade_size = '1024'
    except Exception as e:
        print(f"⚠️  EEVEE settings warning: {e}")
    print(f"✅ OPTIMIZED EEVEE: {EEVEE_SAMPLES} samples, expensive features disabled")


# =============================== UTILS =======================================
def _sanitize(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name)

def randomize_camera(camera_controller):
    """Randomize camera position and rotation for varied perspectives"""
    if not camera_controller:
        return
    
    # Randomize rotation within specified ranges
    rot_x = math.radians(random.uniform(-ROTATION_RANGE_X, ROTATION_RANGE_X))
    rot_y = math.radians(random.uniform(-ROTATION_RANGE_Y, ROTATION_RANGE_Y))
    rot_z = math.radians(random.uniform(-ROTATION_RANGE_Z, ROTATION_RANGE_Z))
    camera_controller.rotation_euler = (rot_x, rot_y, rot_z)
    
    # Randomize distance (via scale)
    scale_factor = 1.0 + random.uniform(-DISTANCE_CLOSER, DISTANCE_FARTHER)
    camera_controller.scale = (scale_factor, scale_factor, scale_factor)
    
    print(f"🎥 Camera: rot({math.degrees(rot_x):.1f}°, {math.degrees(rot_y):.1f}°, {math.degrees(rot_z):.1f}°) scale({scale_factor:.3f})")

def randomize_scene_objects():
    """Randomize which objects appear in scene (adapted from single-pass system)"""
    # 15% chance of background frame (empty surface only)
    if random.random() < 0.15:
        return {'empty_surface': 6}
    
    visible = {}
    
    # Track empty surface (always present unless occluded)
    visible['empty_surface'] = 6
    
    # Rubber band (10% chance, occludes empty surface)
    if random.random() < 0.10:
        if 'empty_surface' in visible:
            del visible['empty_surface']
    
    # Small screws (0-3 screws randomly placed)
    num_small_screws = random.choices([0, 1, 2, 3], weights=[0.4, 0.3, 0.2, 0.1])[0]
    small_screws = random.sample(range(1, 12), num_small_screws) if num_small_screws else []
    
    for idx in small_screws:
        visible[f'screw_{idx:02d}'] = 0
    
    # Small holes (where screws are not) - Enhanced for better training
    available_small = [i for i in range(1, 12) if i not in small_screws]
    
    # Increase small holes frequency and quantity for better training data
    # 10% chance of hole-heavy scenario (3-5 holes for dedicated training)
    if random.random() < 0.10:
        num_small_holes = random.choices([3, 4, 5], weights=[0.4, 0.4, 0.2])[0]
        print("🕳️  Hole-heavy scenario for enhanced small hole training")
    else:
        # Standard scenario with increased hole probability
        num_small_holes = random.choices([0, 1, 2, 3], weights=[0.2, 0.3, 0.3, 0.2])[0]
    
    small_holes = random.sample(available_small, min(num_small_holes, len(available_small))) if available_small else []
    
    for idx in small_holes:
        visible[f'screw_{idx:02d}_patch'] = 1  # Patch generates hole mask
    
    # Additional bracket holes boost (independent of bracket visibility)
    # 30% chance to show bracket holes even without brackets (for hole training)
    for bracket_pos in [1, 2]:
        for bracket_type in ['A', 'B']:
            if random.random() < 0.15:  # 15% per bracket hole
                hole_name = f'bracket_{bracket_type}{bracket_pos}_hole'
                if hole_name not in [k for k in visible.keys()]:  # Don't duplicate
                    visible[hole_name] = 1
                    print(f"🕳️  Adding standalone {hole_name} for hole training")
    
    # Large screws/holes (left and right sides)
    for side in ['left', 'right']:
        choice = random.choices(['screw', 'hole', 'clean'], weights=[0.40, 0.50, 0.10])[0]
        if choice == 'screw':
            visible[f'screw_{side}'] = 2
        elif choice == 'hole':
            visible[f'screw_{side}_patch'] = 3  # Patch generates hole mask
    
    # Bracket A (keyhole bracket type A)
    num_brackets_a = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
    brackets_a = random.sample([1, 2], num_brackets_a) if num_brackets_a else []
    for idx in brackets_a:
        # Make actual bracket visible (not just hole)
        visible[f'bracket_A{idx}'] = 4
        # 50% chance bracket has hole visible too
        if random.random() < 0.5:
            visible[f'bracket_A{idx}_hole'] = 1  # Small hole
    
    # Bracket B (keyhole bracket type B)
    num_brackets_b = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
    brackets_b = random.sample([1, 2], num_brackets_b) if num_brackets_b else []
    for idx in brackets_b:
        # Make actual bracket visible (not just hole)
        visible[f'bracket_B{idx}'] = 5
        # 50% chance bracket has hole visible too
        if random.random() < 0.5:
            visible[f'bracket_B{idx}_hole'] = 1  # Small hole
    
    return visible

def randomize_bracket_orientations():
    """Add enhanced orientation randomization for brackets to handle upside-down detection"""
    bracket_objects = ['bracket_A1', 'bracket_A2', 'bracket_B1', 'bracket_B2']
    
    # 15% chance of "problematic orientation scenario" for enhanced training
    if random.random() < 0.15:
        print("🎯 ENHANCED: Problematic orientation scenario for bracket training")
        # Force more challenging orientations when in enhancement mode
        orientation_weights = [0.3, 0.4, 0.15, 0.15]  # More upside-down and rotations
    else:
        # Standard orientation distribution  
        orientation_weights = [0.6, 0.2, 0.1, 0.1]
    
    for bracket_name in bracket_objects:
        if bracket_name in bpy.data.objects:
            bracket_obj = bpy.data.objects[bracket_name]
            
            # Enhanced rotation randomization with micro-adjustments for realism
            orientation_choice = random.choices(
                ['normal', 'upside_down', 'rotated_90', 'rotated_270'], 
                weights=orientation_weights
            )[0]
            
            # Add small random micro-rotations (±5°) for more realistic data
            micro_rotation = math.radians(random.uniform(-5, 5))
            
            if orientation_choice == 'upside_down':
                bracket_obj.rotation_euler.z = math.radians(180) + micro_rotation
                print(f"🔄 {bracket_name}: Upside down (180° + {math.degrees(micro_rotation):.1f}°)")
            elif orientation_choice == 'rotated_90':
                bracket_obj.rotation_euler.z = math.radians(90) + micro_rotation
                print(f"🔄 {bracket_name}: Rotated 90° + {math.degrees(micro_rotation):.1f}°")
            elif orientation_choice == 'rotated_270':
                bracket_obj.rotation_euler.z = math.radians(270) + micro_rotation
                print(f"🔄 {bracket_name}: Rotated 270° + {math.degrees(micro_rotation):.1f}°")
            else:
                bracket_obj.rotation_euler.z = 0 + micro_rotation
                print(f"🔄 {bracket_name}: Normal + {math.degrees(micro_rotation):.1f}°")

def randomize_lighting_for_brackets():
    """Enhanced lighting randomization to help with bracket shape detection"""
    
    # 20% chance of enhanced lighting scenario for difficult bracket detection
    if random.random() < 0.20:
        print("💡 ENHANCED: Specialized lighting for bracket detection training")
        enhanced_lighting = True
    else:
        enhanced_lighting = False
    
    # Find light objects in the scene
    light_objects = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
    
    for light in light_objects:
        if enhanced_lighting:
            # More dramatic lighting variations for bracket edge detection
            intensity_factor = random.uniform(0.5, 2.0)  # Wider range
            
            # Randomize light direction more dramatically
            light.rotation_euler = (
                math.radians(random.uniform(-45, 45)),
                math.radians(random.uniform(-45, 45)), 
                math.radians(random.uniform(0, 360))
            )
            
            # Color temperature variation for material distinction
            if hasattr(light.data, 'color'):
                temp_variation = random.uniform(0.8, 1.2)
                light.data.color = (
                    min(1.0, light.data.color[0] * temp_variation),
                    light.data.color[1], 
                    min(1.0, light.data.color[2] / temp_variation)
                )
                
            print(f"💡 {light.name}: Enhanced lighting (intensity: {intensity_factor:.2f})")
            
        else:
            # Standard subtle lighting variations
            intensity_factor = random.uniform(0.8, 1.2)
            
            # Subtle light direction changes
            light.rotation_euler = (
                light.rotation_euler[0] + math.radians(random.uniform(-10, 10)),
                light.rotation_euler[1] + math.radians(random.uniform(-10, 10)),
                light.rotation_euler[2] + math.radians(random.uniform(-15, 15))
            )
        
        # Apply intensity changes
        if hasattr(light.data, 'energy'):
            light.data.energy *= intensity_factor

def add_enhanced_randomization_scenarios():
    """Add special randomization scenarios targeting problematic detection cases"""
    
    # 5% chance of "detection challenge mode" - specifically for training edge cases
    if random.random() < 0.05:
        print("🏆 CHALLENGE MODE: Maximum difficulty scenario for robust training")
        
        # Make scene more challenging by:
        # 1. Adding surface variation
        if 'main_body' in bpy.data.objects:
            body = bpy.data.objects['main_body']
            # Slight rotation to create different surface angles
            body.rotation_euler = (
                math.radians(random.uniform(-3, 3)),
                math.radians(random.uniform(-3, 3)),
                0
            )
            
        # 2. Adding subtle material variations (if materials exist)
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.materials:
                for material in obj.data.materials:
                    if material and hasattr(material.node_tree, 'nodes'):
                        # Find principled BSDF node and vary metallic/roughness slightly
                        principled_nodes = [n for n in material.node_tree.nodes 
                                          if n.type == 'BSDF_PRINCIPLED']
                        for node in principled_nodes:
                            # Subtle metallic variation for bracket materials
                            if hasattr(node.inputs, 'Metallic') and 'bracket' in obj.name.lower():
                                original_metallic = node.inputs['Metallic'].default_value
                                node.inputs['Metallic'].default_value = max(0, min(1, 
                                    original_metallic + random.uniform(-0.1, 0.1)))
                            
                            # Roughness variation for all materials
                            if hasattr(node.inputs, 'Roughness'):
                                original_roughness = node.inputs['Roughness'].default_value
                                node.inputs['Roughness'].default_value = max(0, min(1,
                                    original_roughness + random.uniform(-0.15, 0.15)))

def show_only(objects_visible):
    """
    Show only the requested meshes, but ALWAYS keep camera & lights visible.
    This prevents black frames when reducing visibility.
    """
    names_visible = set(objects_visible)
    for obj in bpy.data.objects:
        if obj.type in {"CAMERA", "LIGHT"}:
            obj.hide_render = False
        elif obj.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            obj.hide_render = (obj.name not in names_visible)
        else:
            # leave other types as-is
            pass

def setup_dual_viewlayers():
    """Create two view layers:
       - 'ViewLayer' for beauty (no passes)
       - 'Mask' for mask generation (we'll use alpha via Film Transparent)
    """
    scene = bpy.context.scene
    if "Mask" not in scene.view_layers:
        scene.view_layers.new("Mask")
    # Ensure both exist and are enabled (we'll toggle per pass)
    if "ViewLayer" in scene.view_layers:
        scene.view_layers["ViewLayer"].use = True
    scene.view_layers["Mask"].use = True

def rebuild_compositor_for_alpha_mask(mask_dir):
    """
    Build compositor for the mask pass: write the ALPHA channel of the Mask view layer.
    This avoids Cryptomatte/Index and works reliably in headless runs.
    """
    scene = bpy.context.scene
    scene.use_nodes = True
    scene.render.film_transparent = True  # background alpha 0, objects alpha 1

    tree = scene.node_tree
    tree.links.clear()
    for n in list(tree.nodes):
        tree.nodes.remove(n)

    rl = tree.nodes.new(type='CompositorNodeRLayers')
    rl.layer = "Mask"

    comp = tree.nodes.new(type='CompositorNodeComposite')
    tree.links.new(rl.outputs['Image'], comp.inputs['Image'])

    out = tree.nodes.new(type='CompositorNodeOutputFile')
    out.base_path = mask_dir
    out.format.file_format = 'PNG'
    out.format.color_mode = 'BW'  # single-channel grayscale
    if len(out.file_slots) == 0:
        out.file_slots.new("mask")

    out.file_slots[0].path = "mask_alpha_"
    tree.links.new(rl.outputs['Alpha'], out.inputs[0])

def disconnect_output_files():
    """Remove links to OUTPUT_FILE nodes (so beauty pass won't rewrite masks)."""
    scene = bpy.context.scene
    if not scene.use_nodes:
        return
    tree = scene.node_tree
    to_remove = []
    for link in list(tree.links):
        if getattr(link.to_node, "type", "") == 'OUTPUT_FILE':
            to_remove.append(link)
    for link in to_remove:
        tree.links.remove(link)

def mask_to_polygons(mask_gray, eps=POLYGON_APPROX_EPS):
    """Convert grayscale mask to simplified polygons for YOLO-seg labels."""
    # Alpha mattes are 0/255; use low threshold to be robust
    _, binary = cv2.threshold(mask_gray, THRESH_FOR_MASK, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for cnt in contours:
        per = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, eps * per, True)
        if len(approx) >= 3:
            polys.append(approx)
    return polys

def overlay_mask(image_path, mask_path, out_path=None, color_bgr=(255, 153, 0), alpha=0.45, draw_edge=True):
    """
    Alpha-blend a colored mask onto the beauty image.
    color_bgr is (B,G,R); default is a bluish/cyan tint.
    """
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    m = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if img is None or m is None:
        return False

    h, w = img.shape[:2]
    overlay = img.copy()
    color = np.zeros_like(img)
    color[:] = color_bgr

    # filled region
    mask_bool = m > 0
    overlay[mask_bool] = (alpha * color[mask_bool] + (1 - alpha) * img[mask_bool]).astype(np.uint8)

    # optional crisp edge
    if draw_edge:
        edges = cv2.Canny(m, 50, 150)
        overlay[edges > 0] = (0, 0, 0)  # black edge line

    out = out_path or image_path
    cv2.imwrite(out, overlay)
    return True

def overlay_mask_with_labels(image_path, mask_path, yolo_labels, out_path=None, color_bgr=(255, 153, 0), alpha=0.45, draw_edge=True):
    """
    Alpha-blend a colored mask onto the beauty image with YOLO labels.
    Includes smart label positioning to avoid overlaps.
    """
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    m = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if img is None or m is None:
        return False

    h, w = img.shape[:2]
    overlay = img.copy()
    color = np.zeros_like(img)
    color[:] = color_bgr

    # filled region
    mask_bool = m > 0
    overlay[mask_bool] = (alpha * color[mask_bool] + (1 - alpha) * img[mask_bool]).astype(np.uint8)

    # optional crisp edge
    if draw_edge:
        edges = cv2.Canny(m, 50, 150)
        overlay[edges > 0] = (0, 0, 0)  # black edge line
    
    # Track label positions to avoid overlaps
    label_positions = []
    
    # Draw YOLO labels if provided
    if yolo_labels:
        for idx, line in enumerate(yolo_labels):
            parts = line.strip().split()
            if len(parts) >= 7:  # class_id + at least 6 coordinates (triangle)
                class_id = int(parts[0])
                coords = [float(x) for x in parts[1:]]
                
                # Convert normalized coordinates to pixels
                points = []
                for i in range(0, len(coords), 2):
                    x = int(coords[i] * w)
                    y = int(coords[i+1] * h)
                    points.append((x, y))
                
                # Draw polygon outline
                pts = np.array(points, np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts], True, (0, 255, 0), 2)
                
                # Add class label with smart positioning
                if points:
                    # Calculate centroid
                    center_x = int(sum(p[0] for p in points) / len(points))
                    center_y = int(sum(p[1] for p in points) / len(points))
                    
                    class_name = CLASSES.get(class_id, f"Class_{class_id}")
                    
                    # Draw text with adjusted position to avoid overlaps
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.5  # Slightly smaller for less overlap
                    thickness = 2
                    (text_width, text_height), baseline = cv2.getTextSize(class_name, font, font_scale, thickness)
                    
                    # Check for overlaps and adjust position
                    text_y = center_y
                    for prev_pos in label_positions:
                        prev_x, prev_y, prev_w, prev_h = prev_pos
                        # If labels would overlap, move this one up or down
                        if abs(center_x - prev_x) < (text_width + prev_w) // 2 + 10:
                            if abs(text_y - prev_y) < (text_height + prev_h) + 5:
                                # Move label up or down based on index
                                if idx % 2 == 0:
                                    text_y = prev_y - text_height - 10
                                else:
                                    text_y = prev_y + prev_h + 10
                    
                    # Keep within image bounds
                    text_y = max(text_height + 5, min(h - 5, text_y))
                    text_x = max(text_width//2 + 5, min(w - text_width//2 - 5, center_x))
                    
                    # Store position for overlap checking
                    label_positions.append((text_x, text_y, text_width, text_height))
                    
                    # Draw line from polygon to label if offset
                    if abs(text_y - center_y) > 10 or abs(text_x - center_x) > 10:
                        cv2.line(overlay, (center_x, center_y), (text_x, text_y), (0, 255, 0), 1)
                    
                    # Draw background rectangle
                    cv2.rectangle(overlay, 
                                (text_x - text_width//2 - 3, text_y - text_height - 3),
                                (text_x + text_width//2 + 3, text_y + 3),
                                (0, 0, 0), -1)
                    
                    # Draw white text
                    cv2.putText(overlay, class_name, 
                              (text_x - text_width//2, text_y),
                              font, font_scale, (255, 255, 255), thickness)

    out = out_path or image_path
    cv2.imwrite(out, overlay)
    return True

def create_embedded_composite(image_path, mask_path, overlay_clean_path, overlay_labeled_path, out_path, target_name="object", num_labels=0):
    """
    Create a single composite image containing:
    - Top left: Original render
    - Top right: Binary mask  
    - Bottom left: Clean overlay (mask + beauty)
    - Bottom right: Overlay with YOLO labels
    """
    # Load images
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    overlay_clean = cv2.imread(overlay_clean_path, cv2.IMREAD_COLOR)
    overlay_labeled = cv2.imread(overlay_labeled_path, cv2.IMREAD_COLOR)
    
    if img is None or mask is None or overlay_clean is None or overlay_labeled is None:
        return False
    
    h, w = img.shape[:2]
    
    # Convert mask to 3-channel for composite and enhance visibility
    mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    # Make mask more visible by enhancing contrast and growing small objects
    if np.any(mask > 0):
        # Grow small masks for better visibility
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_enhanced = cv2.dilate(mask, kernel, iterations=2)
        mask_3ch = cv2.cvtColor(mask_enhanced, cv2.COLOR_GRAY2BGR)
        # Make mask bright white for better contrast
        mask_3ch[mask_enhanced > 0] = [255, 255, 255]
    
    # Resize all images to quarter size for 2x2 grid
    img_small = cv2.resize(img, (w//2, h//2))
    mask_small = cv2.resize(mask_3ch, (w//2, h//2))
    overlay_clean_small = cv2.resize(overlay_clean, (w//2, h//2))
    overlay_labeled_small = cv2.resize(overlay_labeled, (w//2, h//2))
    
    # Create 2x2 composite layout
    top_row = np.hstack([img_small, mask_small])
    bottom_row = np.hstack([overlay_clean_small, overlay_labeled_small])
    composite = np.vstack([top_row, bottom_row])
    
    # Add labels to each quadrant
    cv2.putText(composite, "Original", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(composite, "Mask", (w//2 + 5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(composite, "Clean Overlay", (5, h//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(composite, f"YOLO Labels ({num_labels})", (w//2 + 5, h//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imwrite(out_path, composite)
    return True


# ================================= MAIN ======================================
def main():
    scene = bpy.context.scene
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y

    setup_optimized_eevee()

    # IMPORTANT: disable render border to avoid black frames in fresh scenes
    scene.render.use_border = False
    scene.render.use_crop_to_border = False
    print("✅ Render region disabled (avoid black frames)")

    # Mildly lit world in case lights are weak (best-effort, optional)
    try:
        if scene.world and hasattr(scene.world, "use_nodes") and scene.world.use_nodes:
            nodes = scene.world.node_tree.nodes
            bg = nodes.get("Background")
            if bg:
                bg.inputs["Color"].default_value = (0.04, 0.04, 0.04, 1.0)
                bg.inputs["Strength"].default_value = 1.0
    except Exception as e:
        print(f"⚠️  World setup warning: {e}")

    # Camera setup and initialization
    camera = bpy.data.objects.get("Camera")
    camera_controller = bpy.data.objects.get("camera_controller")
    
    if not camera_controller:
        print("❌ ERROR: camera_controller not found! Camera randomization disabled.")
        camera_controller = None
    else:
        print("✅ Found camera_controller for randomization")
        
    if camera and camera.data:
        camera.data.lens = FOCAL_LENGTH
        print(f"✅ Camera focal length set to {FOCAL_LENGTH}mm")
        
    # Store original camera position for reset later
    orig_rot = camera_controller.rotation_euler.copy() if camera_controller else None
    orig_scale = camera_controller.scale.copy() if camera_controller else None

    # Paths
    project_dir = os.path.dirname(bpy.data.filepath)
    debug_dir = os.path.join(project_dir, OUTPUT_DIR_NAME)
    os.makedirs(debug_dir, exist_ok=True)
    temp_masks_root = os.path.join(debug_dir, "_tmp_masks")
    os.makedirs(temp_masks_root, exist_ok=True)

    # Two layers for dual-pass
    setup_dual_viewlayers()

    # Get all objects that exist in the scene and are in our target list
    available_targets = []
    for obj_name in OBJ_TO_CLASS.keys():
        if bpy.data.objects.get(obj_name):
            available_targets.append(obj_name)
    
    if not available_targets:
        print("⚠️  No target objects found in scene!")
        return
    
    # Always include main_body as the constant base + essential context objects
    essential_objects = [
        "main_body"  # The constant base that mechanical parts attach to
    ]
    
    # Optional context objects (only include if they exist)
    optional_context = [
        "Kitchen", "Kitchen.001", "Kitchen.002", "Kitchen.003", 
        "Floor Basement Floor", "Wall Basement Floor"
    ]
    
    # Always include main_body as the base (required)
    context_objects = []
    for obj_name in essential_objects:
        if bpy.data.objects.get(obj_name):
            context_objects.append(obj_name)
        else:
            print(f"⚠️  Required base object '{obj_name}' not found!")
    
    # Add optional context objects if they exist
    for obj_name in optional_context:
        if bpy.data.objects.get(obj_name):
            context_objects.append(obj_name)

    print(f"\n✅ Found {len(available_targets)} target objects")
    print(f"✅ Using main_body as constant base + {len(context_objects)-1} additional context objects")

    width, height = scene.render.resolution_x, scene.render.resolution_y

    print("\n" + "="*80)
    print("DUAL-PASS EEVEE (desk_scene_17) — mechanical components detection")
    print("="*80)
    print(f"Total renders: {NUM_RENDERS}")
    print(f"Output dir: {debug_dir}")

    # Create frame plan with randomized scene objects  
    frame_plan = []
    for i in range(NUM_RENDERS):
        # Generate random scene for each frame
        visible_objects = randomize_scene_objects()
        
        # Convert visible objects dict to lists for compatibility
        beauty_visible = context_objects + list(visible_objects.keys())
        mask_targets = list(visible_objects.keys())
        
        frame_plan.append({
            "beauty_visible": beauty_visible,
            "mask_targets": mask_targets,
            "visible_objects": visible_objects
        })

    total_time = 0.0
    for i in range(NUM_RENDERS):
        t0 = time.time()
        scene.frame_set(i + 1)
        
        # Randomize camera for each render (varied perspectives)
        if camera_controller:
            randomize_camera(camera_controller)
        
        # Randomize bracket orientations (handle upside-down detection)
        randomize_bracket_orientations()
        
        # Enhanced randomization for problematic detection scenarios
        randomize_lighting_for_brackets()
        add_enhanced_randomization_scenarios()

        plan = frame_plan[i]
        targets = plan["mask_targets"]
        beauty_show = plan["beauty_visible"]
        visible_objects = plan.get("visible_objects", {})

        render_basename = f"render_{i:04d}"
        temp_masks_dir = os.path.join(temp_masks_root, render_basename)
        os.makedirs(temp_masks_dir, exist_ok=True)

        # -------------------- INDIVIDUAL MASK PASSES --------------------
        # Render each target object separately to get individual masks
        object_masks = {}  # Store individual masks for each object
        
        if "Mask" in scene.view_layers:
            scene.view_layers["Mask"].use = True
        if "ViewLayer" in scene.view_layers:
            scene.view_layers["ViewLayer"].use = False
            
        rebuild_compositor_for_alpha_mask(temp_masks_dir)
        
        for obj_name in targets:
            if obj_name == 'empty_surface':  # Skip the surface for mask generation
                continue
                
            # Show only this single object for its mask
            show_only([obj_name])
            
            # Render individual mask
            obj_mask_preview = os.path.join(temp_masks_dir, f"mask_{obj_name}.png")
            scene.render.image_settings.file_format = 'PNG'
            scene.render.filepath = obj_mask_preview
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                bpy.ops.render.render(write_still=True)
            
            # Store the mask path
            frame_tag = f"{scene.frame_current:04d}"
            obj_mask_path = os.path.join(temp_masks_dir, f"mask_alpha_{frame_tag}.png")
            if os.path.exists(obj_mask_path):
                object_masks[obj_name] = obj_mask_path
                # Rename to preserve individual masks
                import shutil
                individual_mask_path = os.path.join(temp_masks_dir, f"mask_{obj_name}_{frame_tag}.png")
                shutil.copy2(obj_mask_path, individual_mask_path)
                object_masks[obj_name] = individual_mask_path

        # -------------------- BEAUTY PASS --------------------
        # Show context objects + target in beauty
        show_only(beauty_show)
        scene.render.film_transparent = False  # opaque beauty

        if "ViewLayer" in scene.view_layers:
            scene.view_layers["ViewLayer"].use = True
        if "Mask" in scene.view_layers:
            scene.view_layers["Mask"].use = False

        # Disconnect mask outputs so beauty pass won't rewrite them
        disconnect_output_files()

        _use_nodes_prev = bpy.context.scene.use_nodes
        bpy.context.scene.use_nodes = False

        # Render beauty JPG
        image_name = f"{render_basename}.jpg"
        image_path = os.path.join(debug_dir, image_name)
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.quality = 90
        scene.render.filepath = image_path
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            bpy.ops.render.render(write_still=True)

        bpy.context.scene.use_nodes = _use_nodes_prev

        # -------------------- COLLECT MASKS + WRITE LABELS --------------------
        label_path = os.path.join(debug_dir, f"{render_basename}.txt")
        lines = []
        
        # Create a combined mask for visualization
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        
        # Process each individual object mask
        for obj_name, mask_path in object_masks.items():
            if os.path.exists(mask_path):
                mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                
                # Add to combined mask
                combined_mask = cv2.bitwise_or(combined_mask, mask_img)
                
                # Get polygons from this object's mask
                polys = mask_to_polygons(mask_img)
                
                # Get class ID for this object
                class_id = visible_objects.get(obj_name)
                if class_id is None:
                    # Try to get from OBJ_TO_CLASS mapping
                    class_id = OBJ_TO_CLASS.get(obj_name)
                
                if class_id is not None and polys:
                    # Generate YOLO labels for this object
                    for poly in polys:
                        coords = poly[:, 0, :].astype(np.float32)
                        coords[:, 0] /= width
                        coords[:, 1] /= height
                        coords_str = " ".join(f"{x:.6f}" for x in coords.flatten())
                        lines.append(f"{class_id} {coords_str}")
        
        # Save the combined mask
        final_mask_path = os.path.join(debug_dir, f"{render_basename}_mask.png")
        cv2.imwrite(final_mask_path, combined_mask)
        
        # Create overlay version WITHOUT labels (beauty + combined mask)
        overlay_path = os.path.join(debug_dir, f"{render_basename}_overlay.jpg")
        overlay_mask(image_path, final_mask_path, out_path=overlay_path, color_bgr=(255, 153, 0), alpha=0.45, draw_edge=True)
        
        # Create overlay version WITH labels (beauty + combined mask + YOLO labels)
        overlay_labeled_path = os.path.join(debug_dir, f"{render_basename}_overlay_labeled.jpg")
        overlay_mask_with_labels(image_path, final_mask_path, lines, out_path=overlay_labeled_path, color_bgr=(255, 153, 0), alpha=0.45, draw_edge=True)

        # Always create the label file
        with open(label_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Create embedded composite file
        composite_path = os.path.join(debug_dir, f"{render_basename}_composite.jpg")
        # Count actual detected objects
        num_detected = len(lines)
        # Use description of all visible objects
        if visible_objects:
            obj_count = len([k for k in visible_objects.keys() if k != 'empty_surface'])
            target_name = f"{obj_count} objects" if obj_count > 1 else list(visible_objects.keys())[0]
        else:
            target_name = "empty scene"
        # Create 4-panel composite with both overlay types
        create_embedded_composite(image_path, final_mask_path, overlay_path, overlay_labeled_path,
                                 composite_path, target_name, num_detected)

        dt = time.time() - t0
        total_time += dt
        # Show object distribution instead of single target
        visible_objects = plan.get("visible_objects", {})
        object_summary = []
        for obj_name, class_id in visible_objects.items():
            if obj_name != 'empty_surface':  # Don't count empty surface as object
                class_name = CLASSES.get(class_id, f"class_{class_id}")
                object_summary.append(class_name)
        
        if object_summary:
            obj_desc = f"{len(object_summary)} objects: {', '.join(object_summary[:3])}{'...' if len(object_summary) > 3 else ''}"
        else:
            obj_desc = "background"
            
        print(f"[{i+1}/{NUM_RENDERS}] {obj_desc} | {image_name} | time {dt:.1f}s")

    # Reset camera to original position
    if camera_controller and orig_rot is not None and orig_scale is not None:
        camera_controller.rotation_euler = orig_rot
        camera_controller.scale = orig_scale
        print("🎥 Camera position reset to original")

    print("\n" + "="*80)
    print("✅ COMPLETE — Check JPG+TXT pairs in desk_renders/")
    print(f"Total time: {total_time:.1f}s | Avg/frame: {total_time/NUM_RENDERS:.1f}s")
    print("📷 Camera angles randomized for each render")
    print("🎯 Object placement randomized for dataset variety")


if __name__ == "__main__":
    main()