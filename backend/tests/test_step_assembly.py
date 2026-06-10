"""Tests for STEP assembly part-name extraction (DAW-118)."""
import pytest

from app.services.step_assembly import (
    is_default_part_name,
    read_step_assembly,
    sanitize_part_name,
)


class TestDefaultNameDetection:
    @pytest.mark.parametrize("name", [
        "Body1", "body 2", "Component3", "Component_4", "Part1",
        "Solid", "COMPOUND", "", "  ", "Part-7", "Body1(2)",
    ])
    def test_default_names(self, name):
        assert is_default_part_name(name) is True

    @pytest.mark.parametrize("name", [
        "Angled Bracket", "rotor", "M4_Bolt", "base_plate",
        "Housing Top", "gear-shaft-01",
    ])
    def test_meaningful_names(self, name):
        assert is_default_part_name(name) is False


class TestSanitizePartName:
    def test_spaces_to_underscores(self):
        assert sanitize_part_name("Angled Bracket", 0) == "Angled_Bracket"

    def test_special_chars_stripped(self):
        assert sanitize_part_name("bolt (M4) #2", 0) == "bolt_M4_2"

    def test_empty_gets_positional_name(self):
        assert sanitize_part_name("", 2) == "part_3"


class TestReadStepAssembly:
    """Round-trip tests using cadquery-generated STEP files."""

    @pytest.fixture(autouse=True)
    def _require_cadquery(self):
        pytest.importorskip("cadquery")

    @pytest.fixture
    def named_assembly_step(self, tmp_path):
        import cadquery as cq

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(40, 40, 4), name="base_plate")
        assembly.add(
            cq.Workplane().cylinder(10, 6),
            name="rotor",
            loc=cq.Location((25, 0, 8)),
        )
        path = tmp_path / "assembly.step"
        assembly.export(str(path)) if hasattr(assembly, "export") else assembly.save(str(path))
        return path

    def test_reads_component_names(self, named_assembly_step, tmp_path):
        result = read_step_assembly(str(named_assembly_step), str(tmp_path / "out"))

        assert result.success
        assert sorted(result.component_names) == ["base_plate", "rotor"]

    def test_exports_one_stl_per_component(self, named_assembly_step, tmp_path):
        from pathlib import Path

        result = read_step_assembly(str(named_assembly_step), str(tmp_path / "out"))

        assert result.success
        for component in result.components:
            stl = Path(component.stl_path)
            assert stl.exists()
            assert stl.stat().st_size > 0

    def test_single_part_file(self, tmp_path):
        import cadquery as cq

        path = tmp_path / "single.step"
        cq.exporters.export(cq.Workplane().box(10, 10, 10), str(path))

        result = read_step_assembly(str(path), str(tmp_path / "out"))

        assert result.success
        assert len(result.components) <= 1

    def test_unreadable_file(self, tmp_path):
        bad = tmp_path / "bad.step"
        bad.write_text("not a step file")

        result = read_step_assembly(str(bad), str(tmp_path / "out"))

        assert result.success is False
