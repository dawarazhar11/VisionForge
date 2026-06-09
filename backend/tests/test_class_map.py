"""Tests for generic .blend class-map resolution (DAW-119)."""
import pytest

from app.blender.class_map import (
    DESK_CLASS_NAMES,
    DESK_OBJ_TO_CLASS,
    auto_class_map,
    build_class_map_payload,
    class_names_from_map,
    is_desk_scene,
    parse_metadata_class_map,
    resolve_blend_class_map,
)


class TestDeskSceneDetection:
    def test_detects_desk_scene_by_signature(self):
        names = ["main_body", "screw_01", "screw_left", "bracket_A1", "Camera"]
        assert is_desk_scene(names) is True

    def test_rejects_unrelated_scene(self):
        names = ["Part_001", "Part_002", "VF_Camera"]
        assert is_desk_scene(names) is False


class TestAutoClassMap:
    def test_one_class_per_mesh(self):
        mapping = auto_class_map(["Bolt_A", "Bolt_B", "Housing"])
        assert mapping == {"Bolt_A": 0, "Bolt_B": 1, "Housing": 2}

    def test_stable_sort_order(self):
        mapping = auto_class_map(["z_part", "a_part", "m_part"])
        assert list(mapping.values()) == [0, 1, 2]
        assert mapping["a_part"] == 0


class TestMetadataClassMap:
    def test_parses_structured_metadata(self):
        metadata = {
            "class_map": {
                "object_to_class": {"Bolt": 0, "Nut": 1},
                "class_names": ["fastener", "nut"],
            }
        }
        parsed = parse_metadata_class_map(metadata)
        assert parsed == ({"Bolt": 0, "Nut": 1}, ["fastener", "nut"])

    def test_returns_none_without_class_map(self):
        assert parse_metadata_class_map({}) is None
        assert parse_metadata_class_map(None) is None


class TestResolveBlendClassMap:
    def test_metadata_takes_priority(self):
        metadata = {
            "class_map": {
                "object_to_class": {"custom_part": 0},
                "class_names": ["part"],
            }
        }
        obj_map, class_names, source = resolve_blend_class_map(
            list(DESK_OBJ_TO_CLASS.keys()), metadata
        )
        assert source == "metadata"
        assert obj_map == {"custom_part": 0}
        assert class_names == ["part"]

    def test_desk_preset_for_legacy_scene(self):
        desk_meshes = list(DESK_OBJ_TO_CLASS.keys())[:12]
        obj_map, class_names, source = resolve_blend_class_map(desk_meshes, None)
        assert source == "desk_preset"
        assert class_names == DESK_CLASS_NAMES
        assert obj_map["screw_01"] == 0
        assert obj_map["main_body"] == 6

    def test_auto_for_generic_scene(self):
        meshes = ["Widget_A", "Widget_B"]
        obj_map, class_names, source = resolve_blend_class_map(meshes, None)
        assert source == "auto"
        assert obj_map == {"Widget_A": 0, "Widget_B": 1}
        assert class_names == ["Widget_A", "Widget_B"]


class TestClassNamesFromMap:
    def test_uses_preset_when_provided(self):
        names = class_names_from_map({"a": 0, "b": 0}, preset_names=["shared"])
        assert names == ["shared"]

    def test_fills_gaps_with_object_names(self):
        mapping = {"screw_01": 0, "screw_02": 0, "hole_01": 1}
        names = class_names_from_map(mapping)
        assert names[0] == "screw_01"
        assert names[1] == "hole_01"


class TestBuildClassMapPayload:
    def test_serialisable_shape(self):
        payload = build_class_map_payload({"a": 0}, ["a"], "auto")
        assert payload == {
            "object_to_class": {"a": 0},
            "class_names": ["a"],
            "source": "auto",
        }
