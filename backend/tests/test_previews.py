"""Tests for render preview generation and preview API endpoints."""
import uuid

import pytest
from fastapi import status
from PIL import Image

from app.models.training_job import TrainingJob
from app.services.preview import PREVIEW_DIR_NAME, generate_render_previews


def make_render_output(directory, n=2, with_labels=True):
    """Create fake render output: PNGs with optional YOLO label files."""
    for i in range(n):
        Image.new("RGB", (64, 48), color=(120, 120, 120)).save(
            directory / f"render_{i:04d}.png"
        )
        if with_labels:
            (directory / f"render_{i:04d}.txt").write_text(
                "0 0.5 0.5 0.4 0.4\n1 0.25 0.25 0.2 0.2\n"
            )


class TestGenerateRenderPreviews:
    def test_generates_one_preview_per_image(self, tmp_path):
        make_render_output(tmp_path, n=3)

        count = generate_render_previews(tmp_path, class_names=["rotor", "stator"])

        assert count == 3
        previews = sorted((tmp_path / PREVIEW_DIR_NAME).glob("*.png"))
        assert [p.name for p in previews] == [
            "render_0000.png", "render_0001.png", "render_0002.png"
        ]

    def test_preview_differs_from_original(self, tmp_path):
        """Boxes drawn means bytes differ from the flat source image."""
        make_render_output(tmp_path, n=1)

        generate_render_previews(tmp_path, class_names=["a", "b"])

        original = (tmp_path / "render_0000.png").read_bytes()
        preview = (tmp_path / PREVIEW_DIR_NAME / "render_0000.png").read_bytes()
        assert preview != original

    def test_images_without_labels_still_copied(self, tmp_path):
        make_render_output(tmp_path, n=2, with_labels=False)

        count = generate_render_previews(tmp_path)

        assert count == 2

    def test_max_images_cap(self, tmp_path):
        make_render_output(tmp_path, n=5)

        count = generate_render_previews(tmp_path, max_images=2)

        assert count == 2

    def test_empty_dir(self, tmp_path):
        assert generate_render_previews(tmp_path) == 0


@pytest.fixture
def render_job_with_previews(db, test_project, tmp_path):
    """A successful render job whose output dir contains previews."""
    make_render_output(tmp_path, n=2)
    generate_render_previews(tmp_path, class_names=["rotor", "stator"])

    job = TrainingJob(
        id=uuid.uuid4(),
        project_id=uuid.UUID(test_project["id"]),
        status="SUCCESS",
        progress=100,
        stage="render",
        config_json={"num_renders": 2},
        metrics_json={"output_dir": str(tmp_path), "preview_count": 2},
    )
    db.add(job)
    db.commit()
    return job


class TestPreviewEndpoints:
    def test_list_previews(self, client, auth_headers, render_job_with_previews):
        response = client.get(
            f"/api/v1/jobs/{render_job_with_previews.id}/previews",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
        assert data["previews"] == ["render_0000.png", "render_0001.png"]

    def test_get_single_preview(self, client, auth_headers, render_job_with_previews):
        response = client.get(
            f"/api/v1/jobs/{render_job_with_previews.id}/previews/render_0000.png",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "image/png"

    def test_path_traversal_rejected(self, client, auth_headers, render_job_with_previews):
        response = client.get(
            f"/api/v1/jobs/{render_job_with_previews.id}/previews/..%2F..%2Fetc%2Fpasswd.png",
            headers=auth_headers,
        )

        assert response.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    def test_previews_404_without_render_output(self, client, auth_headers, db, test_project):
        job = TrainingJob(
            id=uuid.uuid4(),
            project_id=uuid.UUID(test_project["id"]),
            status="SUCCESS",
            progress=100,
            stage="render",
            config_json={},
            metrics_json={},
        )
        db.add(job)
        db.commit()

        response = client.get(
            f"/api/v1/jobs/{job.id}/previews", headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_previews_require_auth(self, client, render_job_with_previews):
        response = client.get(
            f"/api/v1/jobs/{render_job_with_previews.id}/previews"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
