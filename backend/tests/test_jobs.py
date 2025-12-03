"""
Tests for job management endpoints.
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch


class TestJobCreation:
    """Tests for job creation endpoint."""

    @patch("app.workers.tasks.echo_task.delay")
    def test_create_test_job(self, mock_task, client, auth_headers, test_project):
        """Test creating a test job."""
        job_data = {
            "project_id": test_project["id"],
            "job_type": "test",
            "config": {"message": "Test message"}
        }

        # Mock Celery task
        mock_task.return_value.id = "mock-task-id"

        response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["project_id"] == test_project["id"]
        assert data["stage"] == "test"
        assert data["status"] == "PENDING"
        assert data["progress"] == 0
        assert "id" in data

    @patch("app.workers.tasks.render_synthetic_data.delay")
    def test_create_render_job(self, mock_task, client, auth_headers, test_project):
        """Test creating a render job."""
        job_data = {
            "project_id": test_project["id"],
            "job_type": "render",
            "config": {"num_images": 100}
        }

        mock_task.return_value.id = "mock-task-id"

        response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["stage"] == "render"

    @patch("app.workers.tasks.train_yolo_model.delay")
    def test_create_train_job(self, mock_task, client, auth_headers, test_project):
        """Test creating a training job."""
        job_data = {
            "project_id": test_project["id"],
            "job_type": "train",
            "config": {"epochs": 50}
        }

        mock_task.return_value.id = "mock-task-id"

        response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["stage"] == "train"

    def test_create_job_invalid_type(self, client, auth_headers, test_project):
        """Test creating job with invalid type fails."""
        job_data = {
            "project_id": test_project["id"],
            "job_type": "invalid_type",
            "config": {}
        }

        with patch("app.workers.tasks.echo_task.delay") as mock:
            mock.return_value.id = "mock-task-id"
            response = client.post(
                "/api/v1/jobs/",
                json=job_data,
                headers=auth_headers
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid job type" in response.json()["detail"].lower()

    def test_create_job_nonexistent_project(self, client, auth_headers):
        """Test creating job for non-existent project fails."""
        job_data = {
            "project_id": "00000000-0000-0000-0000-000000000000",
            "job_type": "test",
            "config": {}
        }

        response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_job_without_auth(self, client, test_project):
        """Test creating job without authentication fails."""
        job_data = {
            "project_id": test_project["id"],
            "job_type": "test",
            "config": {}
        }

        response = client.post("/api/v1/jobs/", json=job_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJobList:
    """Tests for listing jobs."""

    def test_list_jobs_empty(self, client, auth_headers):
        """Test listing jobs when none exist."""
        response = client.get("/api/v1/jobs/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["jobs"]) == 0

    @patch("app.workers.tasks.echo_task.delay")
    def test_list_jobs_with_data(self, mock_task, client, auth_headers, test_project):
        """Test listing jobs returns created jobs."""
        mock_task.return_value.id = "mock-task-id"

        # Create a job
        job_data = {
            "project_id": test_project["id"],
            "job_type": "test",
            "config": {}
        }
        create_response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )
        job_id = create_response.json()["id"]

        # List jobs
        response = client.get("/api/v1/jobs/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["id"] == job_id

    def test_list_jobs_pagination(self, client, auth_headers):
        """Test job list pagination."""
        response = client.get(
            "/api/v1/jobs/?page=1&page_size=10",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    @patch("app.workers.tasks.echo_task.delay")
    def test_list_jobs_filter_by_project(self, mock_task, client, auth_headers, test_project):
        """Test filtering jobs by project ID."""
        mock_task.return_value.id = "mock-task-id"

        # Create a job
        job_data = {
            "project_id": test_project["id"],
            "job_type": "test",
            "config": {}
        }
        client.post("/api/v1/jobs/", json=job_data, headers=auth_headers)

        # Filter by project
        response = client.get(
            f"/api/v1/jobs/?project_id={test_project['id']}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1

    def test_list_jobs_without_auth(self, client):
        """Test listing jobs without authentication fails."""
        response = client.get("/api/v1/jobs/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJobDetail:
    """Tests for getting job details."""

    @patch("app.workers.tasks.echo_task.delay")
    def test_get_job_success(self, mock_task, client, auth_headers, test_project):
        """Test getting job details by ID."""
        mock_task.return_value.id = "mock-task-id"

        # Create a job
        job_data = {
            "project_id": test_project["id"],
            "job_type": "test",
            "config": {"message": "test"}
        }
        create_response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )
        job_id = create_response.json()["id"]

        # Get job details
        response = client.get(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == job_id
        assert data["project_id"] == test_project["id"]

    def test_get_nonexistent_job(self, client, auth_headers):
        """Test getting non-existent job returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/v1/jobs/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_job_without_auth(self, client):
        """Test getting job without authentication fails."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/jobs/{fake_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJobCancellation:
    """Tests for job cancellation."""

    @patch("app.workers.tasks.echo_task.delay")
    def test_cancel_job_success(self, mock_task, client, auth_headers, test_project):
        """Test successful job cancellation."""
        mock_task.return_value.id = "mock-task-id"

        # Create a job
        job_data = {
            "project_id": test_project["id"],
            "job_type": "test",
            "config": {}
        }
        create_response = client.post(
            "/api/v1/jobs/",
            json=job_data,
            headers=auth_headers
        )
        job_id = create_response.json()["id"]

        # Cancel job
        response = client.delete(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify job is cancelled
        get_response = client.get(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers
        )
        assert get_response.json()["status"] == "CANCELLED"

    def test_cancel_nonexistent_job(self, client, auth_headers):
        """Test cancelling non-existent job."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(
            f"/api/v1/jobs/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
