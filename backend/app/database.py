"""Database configuration and session handling for NinerLife v2."""

from collections.abc import Generator
import os
from pathlib import Path
from typing import Mapping

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent
DATABASE_PATH = BACKEND_DIRECTORY / "ninerlife.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


def normalize_database_url(database_url: str) -> str:
    """Return a SQLAlchemy URL that explicitly uses Psycopg for PostgreSQL."""
    normalized_url = database_url.strip()

    if normalized_url.startswith("postgres://"):
        return normalized_url.replace("postgres://", "postgresql+psycopg://", 1)
    if normalized_url.startswith("postgresql://"):
        return normalized_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return normalized_url


def get_database_url(environ: Mapping[str, str] | None = None) -> str:
    """Use DATABASE_URL when configured, otherwise keep local SQLite as default."""
    environment = os.environ if environ is None else environ
    configured_url = environment.get("DATABASE_URL", "").strip()
    return normalize_database_url(configured_url) if configured_url else DEFAULT_DATABASE_URL


def create_database_engine(database_url: str) -> Engine:
    """Build an engine with options appropriate for SQLite or PostgreSQL."""
    engine_options: dict[str, object] = {}

    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    else:
        engine_options["pool_pre_ping"] = True

    return create_engine(database_url, **engine_options)


DATABASE_URL = get_database_url()
engine = create_database_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class shared by all NinerLife database models."""


def create_database_tables(database_engine: Engine = engine) -> None:
    """Create every registered table that does not already exist."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=database_engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session and always close it after use."""
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
