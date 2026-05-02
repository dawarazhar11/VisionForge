"""
VisionForge Generic STEP Render Script — Blender 5.x

Imports a STL (converted from STEP), reads the feature coordinate database,
renders NUM_RENDERS camera viewpoints from a randomised hemisphere, and
auto-generates YOLO bounding-box annotations by projecting each feature's
3-D location into 2-D image space.

No hardcoded objects, no hardcoded classes — everything comes from env vars.

Environment variables (set by BlenderRunner.render_step_geometry):
  VFORGE_STL_PATH       absolute path to the STL file
  VFORGE_FEATURES_JSON  absolute path to features.json
  VFORGE_OUTPUT_DIR     directory for renders + label files
  VFORGE_NUM_RENDERS    number of images  (default 50)
  VFORGE_RESOLUTION_X   image width px   (default 1920)
  VFORGE_RESOLUTION_Y   image height px  (default 1080)
  VFORGE_EEVEE_SAMPLES  EEVEE sample count (default 32)
"""

import os, sys, json, math, random
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

# ─── Config ──────────────────────────────────────────────────────────────────

STL_PATH        = os.environ["VFORGE_STL_PATH"]
FEATURES_JSON   = os.environ["VFORGE_FEATURES_JSON"]
OUTPUT_DIR      = Path(os.environ["VFORGE_OUTPUT_DIR"])
NUM_RENDERS     = int(os.environ.get("VFORGE_NUM_RENDERS",    "50"))
RESOLUTION_X    = int(os.environ.get("VFORGE_RESOLUTION_X",  "1920"))
RESOLUTION_Y    = int(os.environ.get("VFORGE_RESOLUTION_Y",  "1080"))
EEVEE_SAMPLES   = int(os.environ.get("VFORGE_EEVEE_SAMPLES", "32"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(FEATURES_JSON) as fh:
    _feat_data  = json.load(fh)

FEATURES    = _feat_data["features"]       # list[dict]
CLASS_NAMES = _feat_data["class_names"]    # ordered list of unique type names present

# ─── Scene setup ─────────────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for blk in list(bpy.data.meshes):   bpy.data.meshes.remove(blk)
    for blk in list(bpy.data.cameras):  bpy.data.cameras.remove(blk)
    for blk in list(bpy.data.lights):   bpy.data.lights.remove(blk)


def import_stl(path: str):
    """Import STL and return the merged mesh object."""
    bpy.ops.wm.stl_import(filepath=path)
    imported = list(bpy.context.selected_objects)
    if not imported:
        raise RuntimeError(f"STL import returned no objects: {path}")
    if len(imported) > 1:
        bpy.context.view_layer.objects.active = imported[0]
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def normalize_part(obj, features: list) -> list:
    """
    Centre the part at the world origin and scale it to fit a 2-unit cube.
    Apply the same transformation to every feature coordinate so that
    projections stay aligned with the mesh.

    Returns the transformed features list (copies, originals untouched).
    """
    # Bounding box corners in world space (before any transform)
    corners  = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]

    bbox_min = Vector((min(xs), min(ys), min(zs)))
    bbox_max = Vector((max(xs), max(ys), max(zs)))
    bbox_ctr = (bbox_min + bbox_max) * 0.5
    max_dim  = max(bbox_max.x - bbox_min.x,
                   bbox_max.y - bbox_min.y,
                   bbox_max.z - bbox_min.z)
    scale    = (2.0 / max_dim) if max_dim > 1e-9 else 1.0

    # Move origin to geometry centre, then place at world origin
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = Vector((0.0, 0.0, 0.0))
    obj.scale    = Vector((scale, scale, scale))
    bpy.ops.object.transform_apply(location=True, scale=True)

    # Mirror the same transform onto every feature
    tf_features = []
    for feat in features:
        cx, cy, cz = feat["center"]
        nx, ny, nz = feat["normal"]

        # Translate by -bbox_centre, then scale
        tc = [(cx - bbox_ctr.x) * scale,
              (cy - bbox_ctr.y) * scale,
              (cz - bbox_ctr.z) * scale]

        tf = dict(feat)           # shallow copy — safe, we only reassign scalars
        tf["center"] = tc
        tf["radius"] = (feat.get("radius") or 0.0) * scale
        tf["depth"]  = (feat.get("depth")  or 0.0) * scale
        # Normal is a unit vector — no scaling needed
        tf_features.append(tf)

    print(f"Part normalised: bbox_ctr={bbox_ctr!r}  scale={scale:.6f}")
    return tf_features


def setup_material(obj):
    """Simple metallic grey so features have visual contrast."""
    mat  = bpy.data.materials.new("VF_PartMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.58, 0.60, 0.64, 1.0)
        bsdf.inputs["Metallic"].default_value   = 0.85
        bsdf.inputs["Roughness"].default_value  = 0.25
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_camera() -> bpy.types.Object:
    bpy.ops.object.camera_add(location=(0.0, -4.0, 2.0))
    cam = bpy.context.object
    cam.name = "VF_Camera"
    cam.data.lens = 50
    bpy.context.scene.camera = cam
    return cam


def add_lights():
    """3-point area-light rig."""
    for name, loc, energy in (
        ("VF_Key",   ( 4.0, -3.0,  5.0), 800),
        ("VF_Fill",  (-3.0, -2.0,  3.0), 300),
        ("VF_Back",  ( 0.0,  4.0,  3.0), 200),
    ):
        bpy.ops.object.light_add(type='AREA', location=loc)
        lgt = bpy.context.object
        lgt.name = name
        lgt.data.energy = energy
        lgt.data.size   = 2.0


def setup_eevee():
    scene = bpy.context.scene
    # Blender 5.x: EEVEE Next is now 'BLENDER_EEVEE'
    scene.render.engine = (
        'BLENDER_EEVEE' if bpy.app.version >= (5, 0, 0)
        else 'BLENDER_EEVEE_NEXT'
    )
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    try:
        scene.eevee.taa_render_samples = EEVEE_SAMPLES
    except Exception:
        pass

# ─── Camera randomisation ─────────────────────────────────────────────────────

def randomize_camera(cam):
    """
    Place camera on a hemisphere above the part, pointing at the origin.
    Elevation 20–70° keeps the part fully in frame; azimuth is full 360°.
    Distance randomised between 3.5–6.0 Blender units (part fits in 2-unit cube).
    """
    elev = math.radians(random.uniform(20.0, 70.0))
    azim = random.uniform(0.0, 2.0 * math.pi)
    r    = random.uniform(3.5, 6.0)

    x = r * math.cos(elev) * math.cos(azim)
    y = r * math.cos(elev) * math.sin(azim)
    z = r * math.sin(elev)

    cam.location = (x, y, z)
    direction    = -Vector((x, y, z))          # points toward origin
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def randomize_lights():
    """Subtle per-render lighting variation for dataset diversity."""
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            obj.data.energy *= random.uniform(0.85, 1.20)
            obj.rotation_euler = (
                obj.rotation_euler[0] + math.radians(random.uniform(-10, 10)),
                obj.rotation_euler[1] + math.radians(random.uniform(-10, 10)),
                obj.rotation_euler[2] + math.radians(random.uniform(-15, 15)),
            )

# ─── 3-D → 2-D projection + YOLO bbox ───────────────────────────────────────

def _sample_feature_points(feat: dict) -> list:
    """
    Return a list of 3-D world-space points that bound the feature.
    Tight enough for a usable bbox, sparse enough to be fast.
    """
    cx, cy, cz = feat["center"]
    nx, ny, nz = feat["normal"]
    radius = feat.get("radius") or 0.0
    depth  = feat.get("depth")  or 0.0

    pts = [Vector((cx, cy, cz))]

    if radius > 1e-6:
        normal_v = Vector((nx, ny, nz)).normalized()
        perp1    = normal_v.orthogonal().normalized()
        perp2    = normal_v.cross(perp1).normalized()

        # 8 points around each circular end of the feature
        for end_offset in ([0.0] + ([depth] if depth > 1e-6 else [])):
            end_pt = Vector((cx, cy, cz)) + normal_v * end_offset
            for deg in range(0, 360, 45):
                a = math.radians(deg)
                pts.append(
                    end_pt
                    + radius * (math.cos(a) * perp1 + math.sin(a) * perp2)
                )
    else:
        # Planar feature — approximate square from stored area
        area = (feat.get("properties") or {}).get("area", 0.0)
        if area > 1e-6:
            side  = math.sqrt(area) * 0.5
            nv    = Vector((nx, ny, nz)).normalized()
            p1    = nv.orthogonal().normalized() * side
            p2    = nv.cross(p1.normalized()).normalized() * side
            c     = Vector((cx, cy, cz))
            for sx, sy in ((-1,-1), (-1,1), (1,-1), (1,1)):
                pts.append(c + sx * p1 + sy * p2)

    return pts


def feature_yolo_bbox(scene, cam, feat: dict):
    """
    Compute the YOLO bounding box (xc, yc, w, h) in [0,1] image space.
    Returns None if the feature is behind the camera or out of frame.
    """
    pts_3d = _sample_feature_points(feat)

    xs, ys = [], []
    for pt in pts_3d:
        co = world_to_camera_view(scene, cam, pt)
        # co.z > 0  →  in front of camera
        if co.z > 0.001:
            xs.append(co.x)
            ys.append(1.0 - co.y)   # flip y: Blender 0=bottom, image 0=top

    if not xs:
        return None

    x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
    y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
    w, h   = x1 - x0, y1 - y0

    # Discard degenerate boxes
    if w < 0.005 or h < 0.005 or w > 0.98 or h > 0.98:
        return None

    return (x0 + w * 0.5, y0 + h * 0.5, w, h)

# ─── Main render loop ─────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"VisionForge STEP render  [{NUM_RENDERS} images]")
    print(f"Part STL : {STL_PATH}")
    print(f"Features : {len(FEATURES)}  classes: {CLASS_NAMES}")
    print("=" * 60)

    clear_scene()

    part = import_stl(STL_PATH)
    tf_features = normalize_part(part, FEATURES)
    setup_material(part)

    cam = add_camera()
    add_lights()
    setup_eevee()

    scene = bpy.context.scene
    total_annotations = 0

    for i in range(NUM_RENDERS):
        randomize_camera(cam)
        randomize_lights()

        # ── Render ──
        img_path = OUTPUT_DIR / f"render_{i:04d}.png"
        scene.render.filepath = str(img_path)
        bpy.ops.render.render(write_still=True)

        # ── Labels ──
        lines = []
        for feat in tf_features:
            bbox = feature_yolo_bbox(scene, cam, feat)
            if bbox is None:
                continue
            xc, yc, w, h = bbox
            lines.append(f"{feat['class_index']} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

        label_path = OUTPUT_DIR / f"render_{i:04d}.txt"
        label_path.write_text("\n".join(lines))
        total_annotations += len(lines)

        print(f"Rendering image {i+1}/{NUM_RENDERS}  annotations={len(lines)}")

    print("=" * 60)
    print(f"Done. {NUM_RENDERS} images, {total_annotations} total annotations.")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


main()
