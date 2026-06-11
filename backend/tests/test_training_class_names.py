"""Tests for training class-name resolution (DAW-92)."""
from app.workers.tasks import resolve_training_class_names


class FakeFeature:
    def __init__(self, class_index: int):
        self.class_index = class_index


class TestResolveTrainingClassNames:
    def test_explicit_config_wins(self):
        names, source = resolve_training_class_names(
            {"class_names": ["a", "b"]},
            {"class_names": ["x", "y"]},
            [FakeFeature(0)],
        )
        assert names == ["a", "b"]
        assert source == "config"

    def test_render_job_names_used_for_blend_datasets(self):
        names, source = resolve_training_class_names(
            {},
            {"class_names": ["housing", "shaft"], "class_map_source": "auto"},
            None,
        )
        assert names == ["housing", "shaft"]
        assert source == "render_job"

    def test_render_job_beats_part_features(self):
        names, source = resolve_training_class_names(
            {},
            {"class_names": ["housing", "shaft"]},
            [FakeFeature(0), FakeFeature(1)],
        )
        assert names == ["housing", "shaft"]
        assert source == "render_job"

    def test_part_features_fallback(self):
        names, source = resolve_training_class_names(
            {},
            {"output_dir": "/tmp/x"},  # render metrics without class_names
            [FakeFeature(0), FakeFeature(1)],
        )
        assert source == "part_features"
        assert len(names) == 2

    def test_no_sources_returns_none(self):
        names, source = resolve_training_class_names({}, {}, [])
        assert names is None
        assert source == "none"

    def test_handles_missing_render_metrics(self):
        names, source = resolve_training_class_names({}, None, None)
        assert names is None
        assert source == "none"
