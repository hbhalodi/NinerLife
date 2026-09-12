"""Tests for environment-driven database and production CORS configuration."""

import pytest
from sqlalchemy import create_mock_engine

from backend.app.database import (
    Base,
    DEFAULT_DATABASE_URL,
    create_database_engine,
    get_database_url,
    normalize_database_url,
)
import backend.app.models  # noqa: F401
from backend.app.main import get_cors_origins


def test_database_url_defaults_to_the_existing_local_sqlite_database() -> None:
    """No environment setting must preserve local SQLite development behavior."""
    assert get_database_url({}) == DEFAULT_DATABASE_URL
    assert get_database_url({}).startswith("sqlite:///")


@pytest.mark.parametrize(
    ("configured_url", "expected_url"),
    [
        (
            "postgres://student:secret@db.example/ninerlife",
            "postgresql+psycopg://student:secret@db.example/ninerlife",
        ),
        (
            "postgresql://student:secret@db.example/ninerlife",
            "postgresql+psycopg://student:secret@db.example/ninerlife",
        ),
        (
            "postgresql+psycopg://student:secret@db.example/ninerlife",
            "postgresql+psycopg://student:secret@db.example/ninerlife",
        ),
    ],
)
def test_postgres_urls_are_normalized_for_psycopg(
    configured_url: str,
    expected_url: str,
) -> None:
    """Render-style and standard PostgreSQL URLs must select the Psycopg driver."""
    assert normalize_database_url(configured_url) == expected_url
    assert get_database_url({"DATABASE_URL": configured_url}) == expected_url


def test_postgres_engine_initializes_without_connecting() -> None:
    """PostgreSQL configuration can be constructed without a live server."""
    database_engine = create_database_engine(
        "postgresql+psycopg://student:secret@db.example/ninerlife"
    )

    try:
        assert database_engine.url.get_backend_name() == "postgresql"
        assert database_engine.url.get_driver_name() == "psycopg"
        assert database_engine.pool._pre_ping is True
    finally:
        database_engine.dispose()


def test_postgres_table_creation_path_builds_ddl_without_a_server() -> None:
    """Production startup can prepare all model tables before a first deploy."""
    statements: list[str] = []
    mock_engine = create_mock_engine(
        "postgresql+psycopg://student:secret@db.example/ninerlife",
        lambda sql, *_args, **_kwargs: statements.append(str(sql)),
    )

    Base.metadata.create_all(mock_engine)

    assert any("CREATE TABLE courses" in statement for statement in statements)
    assert any("CREATE TABLE assignments" in statement for statement in statements)
    assert any("CREATE TABLE exams" in statement for statement in statements)


def test_cors_origins_include_only_trusted_local_and_configured_origins() -> None:
    """Production frontend access is explicit rather than a wildcard."""
    assert get_cors_origins({"FRONTEND_ORIGIN": "https://ninerlife.vercel.app/"}) == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ninerlife.vercel.app",
    ]


@pytest.mark.parametrize("origin", ["*", "ninerlife.vercel.app", "https://app.example/path"])
def test_cors_rejects_invalid_configured_origin(origin: str) -> None:
    """A malformed frontend value cannot silently weaken the CORS policy."""
    with pytest.raises(ValueError, match="FRONTEND_ORIGIN"):
        get_cors_origins({"FRONTEND_ORIGIN": origin})
