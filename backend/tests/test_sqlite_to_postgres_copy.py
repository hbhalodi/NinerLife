"""Tests for the explicit, idempotent SQLite-to-target data copy utility."""

from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables
from backend.app.migrations.copy_sqlite_to_postgres import (
    SQLiteCopyError,
    copy_sqlite_data,
    get_postgres_target_url,
)
from backend.app.models import Assignment, Course, Exam


@pytest.fixture
def copy_databases(tmp_path: Path) -> Generator[tuple[Engine, Engine], None, None]:
    """Create independent source and target SQLite databases for copy tests."""
    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.db').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.db').as_posix()}")
    create_database_tables(source_engine)

    try:
        yield source_engine, target_engine
    finally:
        source_engine.dispose()
        target_engine.dispose()


def seed_source_data(source_engine: Engine) -> None:
    """Seed source records, including identical assignments, for idempotency checks."""
    source_session_factory = sessionmaker(bind=source_engine, expire_on_commit=False)
    with source_session_factory() as source_session:
        software_course = Course(name="Software Engineering", code="ITSC 3155")
        math_course = Course(name="Calculus", code="MATH 1241")
        source_session.add_all([software_course, math_course])
        source_session.flush()
        source_session.add_all(
            [
                Assignment(
                    name="Project proposal",
                    course_id=software_course.id,
                    due=date(2026, 10, 1),
                    difficulty="High",
                    estimated_hours=4,
                    completed=False,
                ),
                Assignment(
                    name="Project proposal",
                    course_id=software_course.id,
                    due=date(2026, 10, 1),
                    difficulty="High",
                    estimated_hours=4,
                    completed=False,
                ),
                Assignment(
                    name="Problem set",
                    course_id=math_course.id,
                    due=date(2026, 10, 3),
                    difficulty="Medium",
                    estimated_hours=2.5,
                    completed=True,
                ),
                Exam(
                    name="Calculus midterm",
                    course_id=math_course.id,
                    exam_date=date(2026, 10, 5),
                    difficulty="High",
                    estimated_study_hours=6,
                    completed=False,
                ),
            ]
        )
        source_session.commit()


def test_copy_preserves_records_relationships_and_source_data(
    copy_databases: tuple[Engine, Engine],
) -> None:
    """A first copy preserves all records and their Course relationships."""
    source_engine, target_engine = copy_databases
    seed_source_data(source_engine)

    summary = copy_sqlite_data(source_engine, target_engine)

    assert summary.courses_created == 2
    assert summary.assignments_created == 3
    assert summary.exams_created == 1
    with sessionmaker(bind=source_engine)() as source_session:
        assert len(source_session.scalars(select(Course)).all()) == 2
        assert len(source_session.scalars(select(Assignment)).all()) == 3
        assert len(source_session.scalars(select(Exam)).all()) == 1
    with sessionmaker(bind=target_engine)() as target_session:
        target_courses = target_session.scalars(select(Course).order_by(Course.code)).all()
        target_assignments = target_session.scalars(select(Assignment)).all()
        target_exam = target_session.scalar(select(Exam))

        assert [course.code for course in target_courses] == ["ITSC 3155", "MATH 1241"]
        assert len(target_assignments) == 3
        assert target_exam is not None
        assert target_exam.course.code == "MATH 1241"
        assert all(assignment.course is not None for assignment in target_assignments)


def test_copy_is_idempotent_on_a_second_run(
    copy_databases: tuple[Engine, Engine],
) -> None:
    """Rerunning the same source does not create duplicates in the target."""
    source_engine, target_engine = copy_databases
    seed_source_data(source_engine)
    copy_sqlite_data(source_engine, target_engine)

    second_summary = copy_sqlite_data(source_engine, target_engine)

    assert second_summary.courses_created == 0
    assert second_summary.courses_reused == 2
    assert second_summary.assignments_created == 0
    assert second_summary.assignments_skipped == 3
    assert second_summary.exams_created == 0
    assert second_summary.exams_skipped == 1
    with sessionmaker(bind=target_engine)() as target_session:
        assert len(target_session.scalars(select(Assignment)).all()) == 3
        assert len(target_session.scalars(select(Exam)).all()) == 1


def test_copy_rolls_back_when_a_target_course_conflicts(
    copy_databases: tuple[Engine, Engine],
) -> None:
    """A conflicting Course code fails before copying related records."""
    source_engine, target_engine = copy_databases
    seed_source_data(source_engine)
    create_database_tables(target_engine)
    with sessionmaker(bind=target_engine)() as target_session:
        target_session.add(Course(name="Different name", code="ITSC 3155"))
        target_session.commit()

    with pytest.raises(SQLiteCopyError, match="different name"):
        copy_sqlite_data(source_engine, target_engine)

    with sessionmaker(bind=target_engine)() as target_session:
        assert len(target_session.scalars(select(Course)).all()) == 1
        assert target_session.scalars(select(Assignment)).all() == []
        assert target_session.scalars(select(Exam)).all() == []


def test_copy_command_requires_a_postgres_database_url() -> None:
    """The explicit CLI must never treat local SQLite as the copy target."""
    with pytest.raises(SQLiteCopyError, match="DATABASE_URL"):
        get_postgres_target_url({})

    assert get_postgres_target_url(
        {"DATABASE_URL": "postgres://student:secret@db.example/ninerlife"}
    ) == "postgresql+psycopg://student:secret@db.example/ninerlife"

    with pytest.raises(SQLiteCopyError, match="PostgreSQL"):
        get_postgres_target_url({"DATABASE_URL": "sqlite:///not-a-target.db"})
