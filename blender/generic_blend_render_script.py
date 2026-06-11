"""
VisionForge Generic .blend Render Script — Blender 5.x

Renders synthetic training images from any loaded .blend file using a
configurable object→class map. No hardcoded desk objects required.

The .blend file is opened by Blender before this script runs.

Environment variables (set by BlenderRunner.render_blend_geometry):
  VFORGE_OUTPUT_DIR         directory for PNG + YOLO label files
  VFORGE_NUM_RENDERS        image count (default 15)
  VFORGE_RESOLUTION_X/Y     output resolution
  VFORGE_EEVEE_SAMPLES      EEVEE sample count
  VFORGE_CLASS_MAP_JSON     optional path to class_map.json (metadata / preset)
"""

import json
import math
import os
import random
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

# ─── Config ──────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(os.environ["VFORGE_OUTPUT_DIR"])
NUM_RENDERS = int(os.environ.get("VFORGE_NUM_RENDERS", "15"))
RESOLUTION_X = int(os.environ.get("VFORGE_RESOLUTION_X", "1920"))
RESOLUTION_Y = int(os.environ.get("VFORGE_RESOLUTION_Y", "1080"))
EEVEE_SAMPLES = int(os.environ.get("VFORGE_EEVEE_SAMPLES", "64"))
CLASS_MAP_PATH = os.environ.get("VFORGE_CLASS_MAP_JSON", "")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Legacy desk preset (mirrors backend/app/blender/class_map.py)
DESK_OBJ_TO_CLASS = {
    "screw_01": 0, "screw_02": 0, "screw_03": 0, "screw_04": 0, "screw_05": 0,
    "screw_06": 0, "screw_07": 0, "screw_08": 0, "screw_09": 0, "screw_10": 0,
    "screw_11": 0,
    "screw_left": 2, "screw_right": 2,
    "screw_01_patch": 1, "screw_02_patch": 1, "screw_03_patch": 1, "screw_04_patch": 1,
    "screw_05_patch": 1, "screw_06_patch": 1, "screw_07_patch": 1, "screw_08_patch": 1,
    "screw_09_patch": 1, "screw_10_patch": 1, "screw_11_patch": 1,
    "large_screw_hole_left": 3, "large_screw_hole_right": 3,
    "screw_left_patch": 3, "screw_right_patch": 3,
    "bracket_A1": 4, "bracket_A2": 4,
    "bracket_A1_hole": 1, "bracket_A2_hole": 1,
    "bracket_B1": 5, "bracket_B2": 5,
    "bracket_B1_hole": 1, "bracket_B2_hole": 1,
    "main_body": 6, "empty_surface": 6,
    "dead_patch": 6, "dead_patch.001": 6, "dead_patch.002": 6, "dead_patch.003": 6,
    "dead_patch.004": 6, "dead_patch.005": 6, "dead_patch.006": 6,
    "rubber_band": 6,
}
DESK_CLASS_NAMES = [
    "small_screw", "small_hole", "large_screw", "large_hole",
    "bracket_A", "bracket_B", "surface",
]
DESK_SIGNATURE = {"main_body", "screw_01", "screw_left", "screw_right", "bracket_A1"}

SKIP_MESH_NAMES = frozenset({"Plane", "Background"})


def list_mesh_objects():
    return [
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name not in SKIP_MESH_NAMES
    ]


def is_desk_scene(mesh_names):
    names = set(mesh_names)
    return len(names & DESK_SIGNATURE) >= 3 or len(names & set(DESK_OBJ_TO_CLASS.keys())) >= 10


def auto_class_map(mesh_names):
    unique = sorted(set(mesh_names))
    return {name: idx for idx, name in enumerate(unique)}


def class_names_from_map(obj_to_class, preset=None):
    if preset is not None:
        return list(preset)
    if not obj_to_class:
        return []
    max_idx = max(obj_to_class.values())
    names = [f"class_{i}" for i in range(max_idx + 1)]
    for obj_name, class_idx in sorted(obj_to_class.items()):
        if names[class_idx].startswith("class_"):
            names[class_idx] = obj_name
    return names


def resolve_class_map(mesh_names):
    if CLASS_MAP_PATH and Path(CLASS_MAP_PATH).exists():
        data = json.loads(Path(CLASS_MAP_PATH).read_text())
        obj_map = {str(k): int(v) for k, v in data["object_to_class"].items()}
        class_names = data.get("class_names") or class_names_from_map(obj_map)
        return obj_map, class_names, data.get("source", "metadata")

    if is_desk_scene(mesh_names):
        return dict(DESK_OBJ_TO_CLASS), list(DESK_CLASS_NAMES), "desk_preset"

    obj_map = auto_class_map(mesh_names)
    return obj_map, class_names_from_map(obj_map), "auto"


def ensure_camera():
    scene = bpy.context.scene
    if scene.camera is not None:
        return scene.camera
    bpy.ops.object.camera_add(location=(0.0, -4.0, 2.0))
    cam = bpy.context.object
    cam.name = "VF_Camera"
    cam.data.lens = 50
    scene.camera = cam
    return cam


def ensure_lights():
    if any(obj.type == "LIGHT" for obj in bpy.data.objects):
        return
    for name, loc, energy in (
        ("VF_Key", (4.0, -3.0, 5.0), 800),
        ("VF_Fill", (-3.0, -2.0, 3.0), 300),
        ("VF_Back", (0.0, 4.0, 3.0), 200),
    ):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lgt = bpy.context.object
        lgt.name = name
        lgt.data.energy = energy
        lgt.data.size = 2.0


def setup_eevee():
    scene = bpy.context.scene
    scene.render.engine = (
        "BLENDER_EEVEE" if bpy.app.version >= (5, 0, 0) else "BLENDER_EEVEE_NEXT"
    )
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    try:
        scene.eevee.taa_render_samples = EEVEE_SAMPLES
    except Exception:
        pass


def randomize_camera(cam):
    elev = math.radians(random.uniform(20.0, 70.0))
    azim = random.uniform(0.0, 2.0 * math.pi)
    r = random.uniform(3.5, 6.0)
    x = r * math.cos(elev) * math.cos(azim)
    y = r * math.cos(elev) * math.sin(azim)
    z = r * math.sin(elev)
    cam.location = (x, y, z)
    direction = -Vector((x, y, z))
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def randomize_lights():
    for obj in bpy.data.objects:
        if obj.type != "LIGHT":
            continue
        obj.data.energy *= random.uniform(0.85, 1.20)
        obj.rotation_euler = (
            obj.rotation_euler[0] + math.radians(random.uniform(-10, 10)),
            obj.rotation_euler[1] + math.radians(random.uniform(-10, 10)),
            obj.rotation_euler[2] + math.radians(random.uniform(-15, 15)),
        )


def mesh_yolo_bbox(scene, cam, obj):
    xs, ys = [], []
    for corner in obj.bound_box:
        pt = obj.matrix_world @ Vector(corner)
        co = world_to_camera_view(scene, cam, pt)
        if co.z > 0.001:
            xs.append(co.x)
            ys.append(1.0 - co.y)

    if not xs:
        return None

    x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
    y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
    w, h = x1 - x0, y1 - y0
    if w < 0.005 or h < 0.005 or w > 0.98 or h > 0.98:
        return None
    return (x0 + w * 0.5, y0 + h * 0.5, w, h)


def main():
    meshes = list_mesh_objects()
    mesh_names = [m.name for m in meshes]
    obj_to_class, class_names, source = resolve_class_map(mesh_names)

    annotated = [
        (obj, obj_to_class[obj.name])
        for obj in meshes
        if obj.name in obj_to_class
    ]

    print("=" * 60)
    print(f"VisionForge generic .blend render  [{NUM_RENDERS} images]")
    print(f"Meshes: {len(meshes)}  annotated: {len(annotated)}  source: {source}")
    print(f"Classes: {class_names}")
    print("=" * 60)

    (OUTPUT_DIR / "class_map.json").write_text(json.dumps({
        "object_to_class": obj_to_class,
        "class_names": class_names,
        "source": source,
    }, indent=2))

    cam = ensure_camera()
    ensure_lights()
    setup_eevee()
    scene = bpy.context.scene

    # Desk scenes ship with a tuned camera rig — only randomise for auto/generic scenes
    use_camera_randomisation = source == "auto"

    total_annotations = 0
    for i in range(NUM_RENDERS):
        if use_camera_randomisation:
            randomize_camera(cam)
            randomize_lights()

        img_path = OUTPUT_DIR / f"render_{i:04d}.png"
        scene.render.filepath = str(img_path)
        bpy.ops.render.render(write_still=True)

        lines = []
        for obj, class_idx in annotated:
            bbox = mesh_yolo_bbox(scene, cam, obj)
            if bbox is None:
                continue
            xc, yc, w, h = bbox
            lines.append(f"{class_idx} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

        label_path = OUTPUT_DIR / f"render_{i:04d}.txt"
        label_path.write_text("\n".join(lines))
        total_annotations += len(lines)
        print(f"Rendering image {i + 1}/{NUM_RENDERS}  annotations={len(lines)}")

    print("=" * 60)
    print(f"VisionForge Done. {NUM_RENDERS} images, {total_annotations} annotations.")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


main()
