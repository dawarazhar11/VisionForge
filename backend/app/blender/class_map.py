"""
Class-map resolution for generic .blend rendering (DAW-119).

Maps Blender mesh object names to YOLO class indices. Supports:
  1. Explicit map in project metadata_json["class_map"]
  2. Legacy desk-scene preset (scene17)
  3. Auto-discovery (one class per mesh object)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Legacy desk-scene mapping (eevee_desk_scene17_dualpass.py)
DESK_OBJ_TO_CLASS: Dict[str, int] = {
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
    "main_body": 6,
    "empty_surface": 6,
    "dead_patch": 6, "dead_patch.001": 6, "dead_patch.002": 6, "dead_patch.003": 6,
    "dead_patch.004": 6, "dead_patch.005": 6, "dead_patch.006": 6,
    "rubber_band": 6,
}

DESK_CLASS_NAMES: List[str] = [
    "small_screw",
    "small_hole",
    "large_screw",
    "large_hole",
    "bracket_A",
    "bracket_B",
    "surface",
]

# Objects that strongly indicate the bundled desk scene
DESK_SCENE_SIGNATURE = frozenset({
    "main_body", "screw_01", "screw_left", "screw_right", "bracket_A1",
})

DESK_SCENE_MIN_SIGNATURE_MATCHES = 3


def is_desk_scene(mesh_object_names: List[str]) -> bool:
    """Return True when the scene looks like the legacy desk assembly."""
    names = set(mesh_object_names)
    matches = len(names & DESK_SCENE_SIGNATURE)
    mapped = len(names & set(DESK_OBJ_TO_CLASS.keys()))
    return matches >= DESK_SCENE_MIN_SIGNATURE_MATCHES or mapped >= 10


def auto_class_map(mesh_object_names: List[str]) -> Dict[str, int]:
    """Assign one YOLO class per unique mesh object (sorted for stability)."""
    unique = sorted(set(mesh_object_names))
    return {name: idx for idx, name in enumerate(unique)}


def class_names_from_map(
    object_to_class: Dict[str, int],
    preset_names: Optional[List[str]] = None,
) -> List[str]:
    """Build ordered class name list from an object→index map."""
    if preset_names is not None:
        return list(preset_names)

    if not object_to_class:
        return []

    max_idx = max(object_to_class.values())
    names = [f"class_{i}" for i in range(max_idx + 1)]
    for obj_name, class_idx in sorted(object_to_class.items()):
        if names[class_idx].startswith("class_"):
            names[class_idx] = obj_name
    return names


def parse_metadata_class_map(metadata: Optional[Dict[str, Any]]) -> Optional[Tuple[Dict[str, int], List[str]]]:
    """Extract class map from project metadata_json, if present."""
    if not metadata:
        return None

    raw = metadata.get("class_map")
    if not raw:
        return None

    if isinstance(raw, dict) and "object_to_class" in raw:
        obj_map = {str(k): int(v) for k, v in raw["object_to_class"].items()}
        class_names = raw.get("class_names")
        if class_names:
            return obj_map, [str(n) for n in class_names]
        return obj_map, class_names_from_map(obj_map)

    if isinstance(raw, dict):
        obj_map = {str(k): int(v) for k, v in raw.items()}
        return obj_map, class_names_from_map(obj_map)

    return None


def resolve_blend_class_map(
    mesh_object_names: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, int], List[str], str]:
    """
    Resolve object→class mapping for a .blend scene.

    Returns:
        (object_to_class, class_names, source) where source is
        'metadata', 'desk_preset', or 'auto'.
    """
    from_metadata = parse_metadata_class_map(metadata)
    if from_metadata is not None:
        obj_map, class_names = from_metadata
        return obj_map, class_names, "metadata"

    if is_desk_scene(mesh_object_names):
        return dict(DESK_OBJ_TO_CLASS), list(DESK_CLASS_NAMES), "desk_preset"

    obj_map = auto_class_map(mesh_object_names)
    class_names = class_names_from_map(obj_map)
    return obj_map, class_names, "auto"


def build_class_map_payload(
    object_to_class: Dict[str, int],
    class_names: List[str],
    source: str,
) -> Dict[str, Any]:
    """JSON-serialisable class map written beside render outputs."""
    return {
        "object_to_class": object_to_class,
        "class_names": class_names,
        "source": source,
    }
