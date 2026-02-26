"""Simple tests to verify CoreFoundry functionality."""

import pytest
from fastapi.testclient import TestClient
from corefoundry.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CoreFoundry"
    assert data["version"] == "0.1.0"
    assert "endpoints" in data


def test_openapi_schema(client):
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "CoreFoundry"
    assert schema["info"]["version"] == "0.1.0"


def test_docs_available(client):
    """Test that docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert b"CoreFoundry" in response.content


# Note: The following tests require a PostgreSQL database to be running
# and configured. They are marked to skip if the database is not available.

def test_health_endpoint_structure(client):
    """Test health endpoint returns expected structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "ollama" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
