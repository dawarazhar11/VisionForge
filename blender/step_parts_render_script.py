"""
VisionForge STEP assembly parts render script (DAW-118).

Renders synthetic training images from a multi-component STEP assembly:
one STL per named component, each becoming its own YOLO class. Blender
starts empty; this script imports the STLs listed in the parts manifest.

Environment variables (set by BlenderRunner.render_step_parts):
  VFORGE_PARTS_JSON         manifest: {"parts": [{"name", "stl_path",
                            "class_index"}], "class_names": [...],
                            "source": "step_part_names" | "metadata"}
  VFORGE_OUTPUT_DIR         directory for PNG + YOLO label files
  VFORGE_NUM_RENDERS        image count (default 15)
  VFORGE_RESOLUTION_X/Y     output resolution
  VFORGE_EEVEE_SAMPLES      EEVEE sample count
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

PARTS_JSON = Path(os.environ["VFORGE_PARTS_JSON"])
OUTPUT_DIR = Path(os.environ["VFORGE_OUTPUT_DIR"])
NUM_RENDERS = int(os.environ.get("VFORGE_NUM_RENDERS", "15"))
RESOLUTION_X = int(os.environ.get("VFORGE_RESOLUTION_X", "1920"))
RESOLUTION_Y = int(os.environ.get("VFORGE_RESOLUTION_Y", "1080"))
EEVEE_SAMPLES = int(os.environ.get("VFORGE_EEVEE_SAMPLES", "64"))

# Isolation passes: render each part one-at-a-time with a fixed base/reference
# part visible and the rest hidden, so the model gets clean, unoccluded
# examples of every class. VFORGE_BASE_PART optionally names the base; else the
# largest part is used. VFORGE_ISOLATION_FULL_FRAC is the fraction of frames
# kept as full-assembly renders (for occlusion realism).
ISOLATION = os.environ.get("VFORGE_ISOLATION", "1") not in ("0", "false", "False")
BASE_PART = os.environ.get("VFORGE_BASE_PART", "").strip()
FULL_FRAC = float(os.environ.get("VFORGE_ISOLATION_FULL_FRAC", "0.3"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

manifest = json.loads(PARTS_JSON.read_text())
PARTS = manifest["parts"]
CLASS_NAMES = manifest["class_names"]
SOURCE = manifest.get("source", "step_part_names")


# ─── Scene setup ─────────────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_parts():
    """Import each component STL as a named object; returns [(obj, class_idx)]."""
    imported = []
    for part in PARTS:
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=part["stl_path"])
        new_objs = [o for o in bpy.data.objects if o not in before]
        for obj in new_objs:
            obj.name = part["name"]
            imported.append((obj, int(part["class_index"])))
    return imported


def normalize_assembly(objects):
    """Scale and center the whole assembly to fit a ~2 unit sphere at origin."""
    if not objects:
        return
    mins = Vector((1e18, 1e18, 1e18))
    maxs = Vector((-1e18, -1e18, -1e18))
    for obj in objects:
        for corner in obj.bound_box:
            pt = obj.matrix_world @ Vector(corner)
            mins = Vector(map(min, mins, pt))
            maxs = Vector(map(max, maxs, pt))

    center = (mins + maxs) * 0.5
    extent = max(maxs - mins) or 1.0
    scale = 2.0 / extent

    for obj in objects:
        obj.location = (obj.location - center) * scale
        obj.scale = obj.scale * scale
    bpy.context.view_layer.update()


def setup_materials(objects):
    """Give each part a distinct flat material so parts are distinguishable."""
    random.seed(42)
    for i, obj in enumerate(objects):
        mat = bpy.data.materials.new(name=f"VF_Mat_{i}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            hue = (i * 0.137) % 1.0  # golden-ratio spacing
            import colorsys
            r, g, b = colorsys.hsv_to_rgb(hue, 0.45, 0.7)
            bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.55
        obj.data.materials.clear()
        obj.data.materials.append(mat)


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


def randomize_camera(cam, look_at=None, r_range=(3.5, 6.0)):
    """Place the camera on a random hemisphere point looking at `look_at`
    (origin by default). For isolation passes we aim at the target part so it
    fills the frame."""
    target = look_at if look_at is not None else Vector((0.0, 0.0, 0.0))
    elev = math.radians(random.uniform(20.0, 70.0))
    azim = random.uniform(0.0, 2.0 * math.pi)
    r = random.uniform(*r_range)
    offset = Vector((
        r * math.cos(elev) * math.cos(azim),
        r * math.cos(elev) * math.sin(azim),
        r * math.sin(elev),
    ))
    cam.location = target + offset
    direction = target - cam.location
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


# ─── Annotation ──────────────────────────────────────────────────────────────

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


# ─── Geometry / base-part helpers ────────────────────────────────────────────

def world_bbox_center(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector(map(min, zip(*pts))) if pts else Vector((0, 0, 0))
    mx = Vector(map(max, zip(*pts))) if pts else Vector((0, 0, 0))
    return (mn + mx) * 0.5


def bbox_volume(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector(map(min, zip(*pts)))
    mx = Vector(map(max, zip(*pts)))
    d = mx - mn
    return abs(d.x * d.y * d.z)


def choose_base(annotated):
    """Pick the reference part: explicit VFORGE_BASE_PART if it matches,
    otherwise the largest part by bounding-box volume."""
    if BASE_PART:
        for obj, _ in annotated:
            if obj.name.lower() == BASE_PART.lower():
                return obj
    return max((o for o, _ in annotated), key=bbox_volume, default=None)


def build_schedule(annotated, base_obj):
    """Return a list of visible-object sets, one per frame:
    a fraction of full-assembly frames, the rest isolation frames cycling
    each non-base part (base + that part visible)."""
    all_objs = [o for o, _ in annotated]
    if not ISOLATION or len(all_objs) < 2:
        return [all_objs] * NUM_RENDERS

    full_n = max(1, int(round(NUM_RENDERS * FULL_FRAC)))
    schedule = [all_objs] * full_n

    targets = [o for o, _ in annotated if o is not base_obj]
    iso_n = NUM_RENDERS - full_n
    for k in range(iso_n):
        tgt = targets[k % len(targets)]
        visible = [tgt] if base_obj is None or base_obj is tgt else [base_obj, tgt]
        schedule.append(visible)
    return schedule[:NUM_RENDERS]


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    clear_scene()
    annotated = import_parts()
    objects = [obj for obj, _ in annotated]

    normalize_assembly(objects)
    setup_materials(objects)

    base_obj = choose_base(annotated)
    schedule = build_schedule(annotated, base_obj)

    print("=" * 60)
    print(f"VisionForge STEP parts render  [{NUM_RENDERS} images]")
    print(f"Components: {[o.name for o in objects]}  source: {SOURCE}")
    print(f"Classes: {CLASS_NAMES}")
    print(f"Isolation passes: {ISOLATION}  base part: "
          f"{base_obj.name if base_obj else '(none)'}")
    print("=" * 60)

    (OUTPUT_DIR / "class_map.json").write_text(json.dumps({
        "object_to_class": {p["name"]: int(p["class_index"]) for p in PARTS},
        "class_names": CLASS_NAMES,
        "source": SOURCE,
        "isolation": ISOLATION,
        "base_part": base_obj.name if base_obj else None,
    }, indent=2))

    cam = ensure_camera()
    ensure_lights()
    setup_eevee()
    scene = bpy.context.scene

    total_annotations = 0
    for i, visible in enumerate(schedule):
        visible_set = set(visible)
        is_full = visible_set == set(objects)

        # Show only the parts for this frame; hide the rest from the render.
        for obj, _ in annotated:
            obj.hide_render = obj not in visible_set

        # Aim at the assembly center for full frames, at the target part
        # (the non-base visible object) for isolation frames.
        if is_full:
            randomize_camera(cam)
        else:
            tgt = next((o for o in visible if o is not base_obj), visible[0])
            randomize_camera(cam, look_at=world_bbox_center(tgt),
                             r_range=(2.0, 4.0))
        randomize_lights()

        img_path = OUTPUT_DIR / f"render_{i:04d}.png"
        scene.render.filepath = str(img_path)
        bpy.ops.render.render(write_still=True)

        lines = []
        for obj, class_idx in annotated:
            if obj not in visible_set:
                continue
            bbox = mesh_yolo_bbox(scene, cam, obj)
            if bbox is None:
                continue
            xc, yc, w, h = bbox
            lines.append(f"{class_idx} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

        label_path = OUTPUT_DIR / f"render_{i:04d}.txt"
        label_path.write_text("\n".join(lines))
        total_annotations += len(lines)
        mode = "full" if is_full else f"iso:{next((o.name for o in visible if o is not base_obj), '?')}"
        print(f"Rendering image {i + 1}/{NUM_RENDERS}  [{mode}]  annotations={len(lines)}")

    print("=" * 60)
    print(f"VisionForge Done. {NUM_RENDERS} images, {total_annotations} annotations.")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


main()
