"""Database configuration and session handling for NinerLife v2."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent
DATABASE_PATH = BACKEND_DIRECTORY / "ninerlife.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

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
