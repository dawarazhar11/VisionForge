"""Tests for model class-name/label endpoints."""
import uuid

import pytest
from fastapi import status

from app.models.training_job import TrainingJob


@pytest.fixture
def successful_train_job(db, test_project):
    """A completed training job with recorded class names."""
    job = TrainingJob(
        id=uuid.uuid4(),
        project_id=uuid.UUID(test_project["id"]),
        status="SUCCESS",
        progress=100,
        stage="train",
        config_json={"epochs": 1},
        metrics_json={"class_names": ["rotor", "stator", "bolt_m4"]},
    )
    db.add(job)
    db.commit()
    return job


class TestModelClassNames:
    def test_get_class_names(self, client, auth_headers, successful_train_job):
        response = client.get(
            f"/api/v1/models/{successful_train_job.id}/class-names",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["class_names"] == ["rotor", "stator", "bolt_m4"]

    def test_get_labels_file(self, client, auth_headers, successful_train_job):
        response = client.get(
            f"/api/v1/models/{successful_train_job.id}/labels",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.text.strip().split("\n") == ["rotor", "stator", "bolt_m4"]

    def test_class_names_404_for_unknown_model(self, client, auth_headers):
        response = client.get(
            f"/api/v1/models/{uuid.uuid4()}/class-names",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_class_names_404_when_not_recorded(self, client, auth_headers, db, test_project):
        job = TrainingJob(
            id=uuid.uuid4(),
            project_id=uuid.UUID(test_project["id"]),
            status="SUCCESS",
            progress=100,
            stage="train",
            config_json={"epochs": 1},
            metrics_json={"model_path": "/x.pt"},
        )
        db.add(job)
        db.commit()

        response = client.get(
            f"/api/v1/models/{job.id}/class-names",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
