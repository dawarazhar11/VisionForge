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


class TestProjectClassMap:
    """Tests for setting and reading the project class map."""

    def test_get_class_map_when_none_set(self, client, auth_headers, test_project):
        """Project without a class map returns 404."""
        response = client.get(
            f"/api/v1/projects/{test_project['id']}/class-map",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_set_and_get_class_map_with_names(self, client, auth_headers, test_project):
        """PATCH a full class map, then read it back."""
        class_map = {
            "object_to_class": {"gear_housing": 0, "shaft": 1, "bolt_m4": 2},
            "class_names": ["housing", "shaft", "bolt"],
        }
        patch_response = client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json={"class_map": class_map},
            headers=auth_headers
        )

        assert patch_response.status_code == status.HTTP_200_OK

        get_response = client.get(
            f"/api/v1/projects/{test_project['id']}/class-map",
            headers=auth_headers
        )

        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["object_to_class"] == class_map["object_to_class"]
        assert data["class_names"] == ["housing", "shaft", "bolt"]
        assert data["source"] == "metadata"

    def test_set_plain_class_map_derives_names(self, client, auth_headers, test_project):
        """A plain {object: index} map derives class names from object names."""
        patch_response = client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json={"class_map": {"rotor": 0, "stator": 1}},
            headers=auth_headers
        )

        assert patch_response.status_code == status.HTTP_200_OK

        get_response = client.get(
            f"/api/v1/projects/{test_project['id']}/class-map",
            headers=auth_headers
        )

        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["class_names"] == ["rotor", "stator"]

    def test_set_invalid_class_map_rejected(self, client, auth_headers, test_project):
        """Malformed class maps are rejected with 422."""
        patch_response = client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json={"class_map": {"object_to_class": "not-a-dict"}},
            headers=auth_headers
        )

        assert patch_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_set_class_map_preserves_name_update(self, client, auth_headers, test_project):
        """class_map and name can be updated in the same PATCH."""
        response = client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json={"name": "Renamed", "class_map": {"part_a": 0}},
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Renamed"

    def test_class_map_requires_auth(self, client, test_project):
        """Class map endpoints require authentication."""
        response = client.get(f"/api/v1/projects/{test_project['id']}/class-map")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


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
