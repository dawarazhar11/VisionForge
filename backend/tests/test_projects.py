"""
Tests for project management endpoints.
"""
import pytest
from fastapi import status
import io


class TestProjectUpload:
    """Tests for project upload endpoint."""

    def test_upload_project_success(self, client, auth_headers, test_project_data, tmp_path):
        """Test successful project file upload."""
        # Create test file
        test_file = tmp_path / "test.blend"
        test_file.write_text("dummy blender file")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/projects/upload",
                files={"file": ("test.blend", f, "application/octet-stream")},
                data=test_project_data,
                headers=auth_headers
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == test_project_data["name"]
        assert data["file_type"] == ".blend"
        assert "id" in data
        assert data["status"] == "uploaded"

    def test_upload_without_auth(self, client, test_project_data, tmp_path):
        """Test upload without authentication fails."""
        test_file = tmp_path / "test.blend"
        test_file.write_text("dummy content")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/projects/upload",
                files={"file": ("test.blend", f)},
                data=test_project_data
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_obj_file(self, client, auth_headers, tmp_path):
        """Test uploading OBJ file."""
        test_file = tmp_path / "test.obj"
        test_file.write_text("# OBJ file")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/projects/upload",
                files={"file": ("test.obj", f)},
                data={"name": "OBJ Test Project"},
                headers=auth_headers
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["file_type"] == ".obj"


class TestProjectList:
    """Tests for listing projects."""

    def test_list_projects_empty(self, client, auth_headers):
        """Test listing projects when none exist."""
        response = client.get("/api/v1/projects/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["projects"]) == 0

    def test_list_projects_with_data(self, client, auth_headers, test_project):
        """Test listing projects returns created projects."""
        response = client.get("/api/v1/projects/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["projects"]) == 1
        assert data["projects"][0]["id"] == test_project["id"]

    def test_list_projects_pagination(self, client, auth_headers):
        """Test project list pagination."""
        response = client.get(
            "/api/v1/projects/?page=1&page_size=10",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_list_projects_without_auth(self, client):
        """Test listing projects without authentication fails."""
        response = client.get("/api/v1/projects/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProjectDetail:
    """Tests for getting project details."""

    def test_get_project_success(self, client, auth_headers, test_project):
        """Test getting project details by ID."""
        response = client.get(
            f"/api/v1/projects/{test_project['id']}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_project["id"]
        assert data["name"] == test_project["name"]

    def test_get_nonexistent_project(self, client, auth_headers):
        """Test getting non-existent project returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/v1/projects/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_project_without_auth(self, client, test_project):
        """Test getting project without authentication fails."""
        response = client.get(f"/api/v1/projects/{test_project['id']}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProjectUpdate:
    """Tests for updating projects."""

    def test_update_project_name(self, client, auth_headers, test_project):
        """Test updating project name."""
        updated_data = {"name": "Updated Project Name"}
        response = client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json=updated_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == updated_data["name"]
        assert data["id"] == test_project["id"]

    def test_update_project_description(self, client, auth_headers, test_project):
        """Test updating project description."""
        updated_data = {"description": "New description"}
        response = client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json=updated_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["description"] == updated_data["description"]


class TestProjectDelete:
    """Tests for deleting projects."""

    def test_delete_project_success(self, client, auth_headers, test_project):
        """Test successful project deletion."""
        response = client.delete(
            f"/api/v1/projects/{test_project['id']}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify project is deleted
        get_response = client.get(
            f"/api/v1/projects/{test_project['id']}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_project(self, client, auth_headers):
        """Test deleting non-existent project."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(
            f"/api/v1/projects/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
