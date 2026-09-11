"""Basic endpoint tests for the NinerLife API foundation."""

import pytest
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


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_cors_preflight_allows_frontend_crud_methods(method: str) -> None:
    """The local Vite frontend should be able to use each CRUD method."""
    response = client.options(
        "/courses",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5173"
    )
    assert method in response.headers["access-control-allow-methods"].split(", ")
    assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_cors_preflight_rejects_unneeded_method() -> None:
    """CORS should not permit methods outside the frontend CRUD contract."""
    response = client.options(
        "/courses",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )

    assert response.status_code == 400
