"""Tests for the explicit NinerLife v1 CSV migration."""

import csv
from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables
from backend.app.migrations.import_v1_csv import (
    CsvMigrationError,
    import_v1_csv,
    preview_v1_csv,
)
from backend.app.models import Assignment, Course

CSV_COLUMNS = ["name", "course", "due", "difficulty", "estimated_hours"]
SessionFactory = sessionmaker[Session]


@pytest.fixture
def temporary_database(
    tmp_path: Path,
) -> Generator[tuple[SessionFactory, Engine], None, None]:
    """Provide a clean temporary SQLite database for a migration test."""
    database_path = tmp_path / "ninerlife-migration-test.db"
    test_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    create_database_tables(test_engine)
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    yield test_session_factory, test_engine

    test_engine.dispose()


def write_csv(
    csv_path: Path,
    rows: list[dict[str, str]],
    columns: list[str] = CSV_COLUMNS,
) -> None:
    """Write controlled CSV input inside pytest's temporary directory."""
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def valid_rows() -> list[dict[str, str]]:
    """Return valid CSV rows spanning two unique courses."""
    return [
        {
            "name": "Python Project",
            "course": "ITSC 3155",
            "due": "2026-09-11",
            "difficulty": "High",
            "estimated_hours": "3.0",
        },
        {
            "name": "API Tests",
            "course": "ITSC 3155",
            "due": "2026-09-15",
            "difficulty": "Medium",
            "estimated_hours": "2.5",
        },
        {
            "name": "Math Quiz",
            "course": "MATH 1241",
            "due": "2026-09-17",
            "difficulty": "Low",
            "estimated_hours": "1.0",
        },
    ]


def count_rows(session_factory: SessionFactory, model: type[object]) -> int:
    """Count rows for a mapped model in a temporary database."""
    with session_factory() as database_session:
        return database_session.scalar(select(func.count()).select_from(model)) or 0


def test_valid_csv_imports_assignments_and_unique_courses(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """Valid values and relationships should survive the import."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / "assignments.csv"
    write_csv(csv_path, valid_rows())

    result = import_v1_csv(csv_path, session_factory)

    assert result.courses_created == 2
    assert result.courses_reused == 0
    assert result.assignments_imported == 3
    assert result.assignments_skipped == 0

    with session_factory() as database_session:
        courses = database_session.scalars(select(Course).order_by(Course.code)).all()
        assignments = database_session.scalars(
            select(Assignment).order_by(Assignment.name)
        ).all()

        assert [(course.name, course.code) for course in courses] == [
            ("ITSC 3155", "ITSC 3155"),
            ("MATH 1241", "MATH 1241"),
        ]
        python_project = next(
            assignment
            for assignment in assignments
            if assignment.name == "Python Project"
        )
        assert python_project.course.code == "ITSC 3155"
        assert python_project.due == date(2026, 9, 11)
        assert python_project.difficulty == "High"
        assert python_project.estimated_hours == 3.0
        assert python_project.completed is False
        assert len(python_project.course.assignments) == 2


def test_existing_course_is_reused(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """A CSV course value should match an existing Course code."""
    session_factory, _ = temporary_database
    with session_factory.begin() as database_session:
        existing_course = Course(
            name="Software Engineering",
            code="ITSC 3155",
        )
        database_session.add(existing_course)

    csv_path = tmp_path / "assignments.csv"
    write_csv(csv_path, [valid_rows()[0]])

    result = import_v1_csv(csv_path, session_factory)

    assert result.courses_created == 0
    assert result.courses_reused == 1
    assert count_rows(session_factory, Course) == 1
    with session_factory() as database_session:
        assignment = database_session.scalar(select(Assignment))
        assert assignment is not None
        assert assignment.course.code == "ITSC 3155"
        assert assignment.course.name == "Software Engineering"


def test_second_migration_skips_duplicate_assignments(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """Running the same migration twice should not duplicate data."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / "assignments.csv"
    write_csv(csv_path, valid_rows())

    first_result = import_v1_csv(csv_path, session_factory)
    second_result = import_v1_csv(csv_path, session_factory)

    assert first_result.assignments_imported == 3
    assert second_result.assignments_imported == 0
    assert second_result.assignments_skipped == 3
    assert second_result.courses_created == 0
    assert second_result.courses_reused == 2
    assert count_rows(session_factory, Course) == 2
    assert count_rows(session_factory, Assignment) == 3


def test_preview_reports_plan_without_writing(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """Dry-run planning should leave both tables empty."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / "assignments.csv"
    write_csv(csv_path, valid_rows())

    preview = preview_v1_csv(csv_path, session_factory)

    assert preview.total_rows == 3
    assert preview.assignments_to_import == 3
    assert preview.assignments_to_skip == 0
    assert [course.action for course in preview.courses] == ["create", "create"]
    assert count_rows(session_factory, Course) == 0
    assert count_rows(session_factory, Assignment) == 0


def test_missing_required_column_fails_clearly(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """A missing CSV column should fail before any database write."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / "missing-column.csv"
    columns = [column for column in CSV_COLUMNS if column != "due"]
    row = {key: value for key, value in valid_rows()[0].items() if key in columns}
    write_csv(csv_path, [row], columns)

    with pytest.raises(CsvMigrationError, match="missing required columns: due"):
        import_v1_csv(csv_path, session_factory)

    assert count_rows(session_factory, Course) == 0
    assert count_rows(session_factory, Assignment) == 0


def test_invalid_date_rolls_back_entire_import(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """An invalid later row should prevent valid earlier rows from importing."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / "invalid-date.csv"
    rows = valid_rows()[:2]
    rows[1] = {**rows[1], "due": "September 15"}
    write_csv(csv_path, rows)

    with pytest.raises(CsvMigrationError, match="Row 3: invalid due date"):
        import_v1_csv(csv_path, session_factory)

    assert count_rows(session_factory, Course) == 0
    assert count_rows(session_factory, Assignment) == 0


def test_invalid_estimated_hours_rolls_back_entire_import(
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """Invalid hours should identify the row and leave the database empty."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / "invalid-hours.csv"
    rows = valid_rows()[:2]
    rows[1] = {**rows[1], "estimated_hours": "several"}
    write_csv(csv_path, rows)

    with pytest.raises(CsvMigrationError, match="Row 3: invalid estimated_hours"):
        import_v1_csv(csv_path, session_factory)

    assert count_rows(session_factory, Course) == 0
    assert count_rows(session_factory, Assignment) == 0


@pytest.mark.parametrize("column", ["name", "course", "difficulty"])
def test_blank_required_text_fails_clearly(
    column: str,
    tmp_path: Path,
    temporary_database: tuple[SessionFactory, Engine],
) -> None:
    """Blank required text should identify its row and create no data."""
    session_factory, _ = temporary_database
    csv_path = tmp_path / f"blank-{column}.csv"
    row = {**valid_rows()[0], column: "   "}
    write_csv(csv_path, [row])

    with pytest.raises(
        CsvMigrationError,
        match=rf"Row 2: '{column}' must not be blank",
    ):
        import_v1_csv(csv_path, session_factory)

    assert count_rows(session_factory, Course) == 0
    assert count_rows(session_factory, Assignment) == 0
