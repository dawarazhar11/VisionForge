"""
Pytest configuration and fixtures for backend tests.
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Monkeypatch JSONB to use JSON for SQLite tests (must be before importing models)
import sqlalchemy.dialects.postgresql as postgresql_dialects
original_jsonb = postgresql_dialects.JSONB


class TestJSONB(JSON):
    """JSONB replacement for SQLite tests."""
    __visit_name__ = 'JSON'


postgresql_dialects.JSONB = TestJSONB
sys.modules['sqlalchemy.dialects.postgresql'].JSONB = TestJSONB

from app.main import app
from app.database import Base, get_db
from app.config import settings


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign key constraints in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a test client with test database dependency override.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """
    Sample user data for testing.
    """
    return {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }


@pytest.fixture
def test_user(client, test_user_data):
    """
    Create a test user and return registration response.
    """
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(client, test_user_data):
    """
    Get authentication headers with valid JWT token.
    """
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 200
    token_data = response.json()
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest.fixture
def test_project_data():
    """
    Sample project data for testing.
    """
    return {
        "name": "Test Project",
        "description": "A test assembly project"
    }


@pytest.fixture
def test_job_data(test_project):
    """
    Sample job data for testing.
    """
    return {
        "project_id": test_project["id"],
        "job_type": "test",
        "config": {"message": "Test job"}
    }


@pytest.fixture
def test_project(client, auth_headers, test_project_data, tmp_path):
    """
    Create a test project by uploading a dummy file.
    """
    # Create a dummy .blend file
    test_file = tmp_path / "test.blend"
    test_file.write_text("dummy blender file content")

    with open(test_file, "rb") as f:
        response = client.post(
            "/api/v1/projects/upload",
            files={"file": ("test.blend", f, "application/octet-stream")},
            data={
                "name": test_project_data["name"],
                "description": test_project_data.get("description", "")
            },
            headers=auth_headers
        )

    assert response.status_code == 201
    return response.json()


# Mark all tests as using asyncio
pytest_plugins = ("pytest_asyncio",)
