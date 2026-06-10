"""Tests for training device fallback and label-task detection."""
import torch

from app.training.runner import detect_label_task, resolve_training_device


class TestResolveTrainingDevice:
    def test_cpu_passthrough(self):
        assert resolve_training_device("cpu") == "cpu"

    def test_cuda_kept_when_available(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
        assert resolve_training_device("0") == "0"
        assert resolve_training_device("0,1") == "0,1"

    def test_falls_back_to_mps_without_cuda(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
        assert resolve_training_device("0") == "mps"

    def test_falls_back_to_cpu_without_accelerators(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
        assert resolve_training_device("0") == "cpu"


class TestDetectLabelTask:
    def test_detect_format(self, tmp_path):
        (tmp_path / "img_0.txt").write_text("0 0.5 0.5 0.2 0.1\n1 0.3 0.3 0.1 0.1\n")
        assert detect_label_task(tmp_path) == "detect"

    def test_segment_format(self, tmp_path):
        (tmp_path / "img_0.txt").write_text("0 0.1 0.1 0.2 0.1 0.2 0.3 0.1 0.3\n")
        assert detect_label_task(tmp_path) == "segment"

    def test_empty_dir_defaults_to_detect(self, tmp_path):
        assert detect_label_task(tmp_path) == "detect"

    def test_skips_empty_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b.txt").write_text("2 0.5 0.5 0.2 0.1\n")
        assert detect_label_task(tmp_path) == "detect"
