"""Tests for training device fallback (CPU-only containers)."""
import torch

from app.training.runner import resolve_training_device


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
