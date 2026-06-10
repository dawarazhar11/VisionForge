"""Create a small non-desk test assembly and save it as a .blend.

Run inside the worker container:
  blender --background --python /app/storage/e2e/make_test_scene.py

Objects use custom names so the generic render pipeline must resolve
classes dynamically (no desk preset match).
"""
import bpy

OUT_PATH = "/app/storage/e2e/generic_parts.blend"

# Wipe default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene

# Ground plane named like a generic part
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
bpy.context.active_object.name = "base_plate"

# A few distinct parts with non-desk names
bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=0.6, location=(-1, 0, 0.3))
bpy.context.active_object.name = "rotor"

bpy.ops.mesh.primitive_cube_add(size=0.5, location=(1, 0, 0.25))
bpy.context.active_object.name = "stator"

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 1, 0.2))
bpy.context.active_object.name = "bolt_m4"

# Camera
bpy.ops.object.camera_add(location=(4, -4, 3), rotation=(1.1, 0, 0.8))
scene.camera = bpy.context.active_object

# Light
bpy.ops.object.light_add(type="SUN", location=(2, -2, 5))

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"Saved test scene to {OUT_PATH}")
