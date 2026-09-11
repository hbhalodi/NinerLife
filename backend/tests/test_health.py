"""Basic endpoint tests for the NinerLife API foundation."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check_returns_expected_response() -> None:
    """The health endpoint should confirm that the API is available."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "NinerLife API"}
