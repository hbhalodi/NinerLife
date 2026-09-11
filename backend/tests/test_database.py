"""Tests for the NinerLife SQLAlchemy database foundation."""

from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables
from backend.app.models import Assignment, Course


@pytest.fixture
def temporary_database(
    tmp_path: Path,
) -> Generator[tuple[Session, Engine], None, None]:
    """Create an isolated SQLite database and session for each test."""
    database_path = tmp_path / "ninerlife-test.db"
    test_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    create_database_tables(test_engine)
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with test_session_factory() as database_session:
        yield database_session, test_engine

    test_engine.dispose()


def test_database_tables_can_be_created(
    temporary_database: tuple[Session, Engine],
) -> None:
    """Both Phase 2 tables should be present in a temporary database."""
    _, test_engine = temporary_database

    assert set(inspect(test_engine).get_table_names()) == {
        "assignments",
        "courses",
    }


def test_assignment_can_be_linked_to_its_course(
    temporary_database: tuple[Session, Engine],
) -> None:
    """A course should expose its assignments and vice versa."""
    database_session, _ = temporary_database
    course = Course(name="Software Engineering", code="ITSC 3155")
    assignment = Assignment(
        name="NinerLife Phase 2",
        course=course,
        due=date(2026, 9, 18),
        difficulty="High",
        estimated_hours=4.0,
    )

    database_session.add(assignment)
    database_session.commit()

    saved_course = database_session.scalar(select(Course))
    saved_assignment = database_session.scalar(select(Assignment))

    assert saved_course is not None
    assert saved_assignment is not None
    assert saved_assignment.course_id == saved_course.id
    assert saved_assignment.course is saved_course
    assert saved_course.assignments == [saved_assignment]
    assert saved_assignment.completed is False
