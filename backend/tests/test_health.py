"""Basic endpoint tests for the NinerLife API foundation."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check_returns_expected_response() -> None:
    """The health endpoint should confirm that the API is available."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "NinerLife API"}


def test_health_check_allows_local_vite_origin() -> None:
    """The Vite development app should be allowed to read API responses."""
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_health_check_does_not_allow_unknown_origin() -> None:
    """CORS should remain restricted to known local development origins."""
    response = client.get(
        "/health",
        headers={"Origin": "https://example.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
