"""Tests for the read-only NinerLife v1 deadline and priority engine."""

from collections.abc import Generator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables, get_db
from backend.app.main import app
from backend.app.models import Assignment, Course
from backend.app.services.prioritization import (
    calculate_priority,
    days_until_due,
    get_deadline_status,
    normalize_difficulty,
)

SessionFactory = sessionmaker[Session]
PrioritizationTestContext = tuple[TestClient, SessionFactory]


@pytest.fixture
def prioritization_test_context(
    tmp_path: Path,
) -> Generator[PrioritizationTestContext, None, None]:
    """Provide a temporary database for each insight-endpoint test."""
    database_path = tmp_path / "ninerlife-prioritization-test.db"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    create_database_tables(test_engine)
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as database_session:
            yield database_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        yield client, test_session_factory
    finally:
        client.close()
        app.dependency_overrides.clear()
        test_engine.dispose()


@pytest.mark.parametrize(
    ("days_remaining", "expected_status"),
    [
        (-1, "Overdue"),
        (0, "Due Today"),
        (1, "Due Soon"),
        (2, "Due Soon"),
        (3, "Upcoming"),
    ],
)
def test_deadline_status_boundaries(
    days_remaining: int,
    expected_status: str,
) -> None:
    """Every preserved v1 deadline boundary should return its display value."""
    assert get_deadline_status(days_remaining) == expected_status


def test_days_until_due_uses_signed_calendar_days() -> None:
    """The pure day calculation should support past, current, and future dates."""
    reference_date = date(2026, 9, 11)

    assert days_until_due(date(2026, 9, 10), reference_date) == -1
    assert days_until_due(reference_date, reference_date) == 0
    assert days_until_due(date(2026, 9, 13), reference_date) == 2


@pytest.mark.parametrize(
    ("difficulty", "days_remaining", "expected_priority"),
    [
        ("High", 2, "Critical"),
        ("High", 3, "High"),
        ("High", 5, "High"),
        ("High", 6, "Medium"),
        ("Medium", 2, "High"),
        ("Medium", 3, "Medium"),
        ("Medium", 5, "Medium"),
        ("Medium", 6, "Low"),
        ("Low", 2, "Medium"),
        ("Low", 3, "Low"),
        ("Low", 6, "Low"),
    ],
)
def test_priority_branches(
    difficulty: str,
    days_remaining: int,
    expected_priority: str,
) -> None:
    """Every High, Medium, and Low v1 priority branch should be preserved."""
    assert calculate_priority(days_remaining, difficulty) == expected_priority


def test_difficulty_normalization_is_case_insensitive() -> None:
    """Difficulty comparison should be case-insensitive with stable display text."""
    assert normalize_difficulty("  hIgH  ") == "High"
    assert calculate_priority(4, "mEdIuM") == "Medium"
    assert calculate_priority(0, "LOW") == "Medium"


@pytest.mark.parametrize("difficulty", ["", "urgent", "  unknown  ", None])
def test_invalid_difficulty_is_rejected(difficulty: object) -> None:
    """Unknown difficulty values must not receive a fabricated priority."""
    with pytest.raises(ValueError, match="Difficulty must be Low, Medium, or High"):
        calculate_priority(2, difficulty)


def add_insight_records(session_factory: SessionFactory, today: date) -> None:
    """Create valid records with both open and completed assignment states."""
    with session_factory() as database_session:
        course = Course(name="Software Engineering", code="ITSC 3155")
        database_session.add_all(
            [
                course,
                Assignment(
                    name="Completed today",
                    course=course,
                    due=today,
                    difficulty="hIgH",
                    estimated_hours=2.5,
                    completed=True,
                ),
                Assignment(
                    name="Open in three days",
                    course=course,
                    due=today + timedelta(days=3),
                    difficulty="medium",
                    estimated_hours=4,
                    completed=False,
                ),
            ]
        )
        database_session.commit()


def test_insight_endpoint_includes_course_and_completed_behavior(
    prioritization_test_context: PrioritizationTestContext,
) -> None:
    """Insights should include canonical difficulty, Course data, and completion."""
    client, session_factory = prioritization_test_context
    today = date.today()
    add_insight_records(session_factory, today)

    response = client.get("/assignments/insights")

    assert response.status_code == 200
    insights = response.json()
    assert [insight["name"] for insight in insights] == [
        "Completed today",
        "Open in three days",
    ]
    assert insights[0] == {
        "id": 1,
        "name": "Completed today",
        "course_id": 1,
        "course": {"id": 1, "code": "ITSC 3155", "name": "Software Engineering"},
        "due": today.isoformat(),
        "difficulty": "High",
        "estimated_hours": 2.5,
        "completed": True,
        "days_until_due": 0,
        "deadline_status": "Due Today",
        "priority": "Critical",
    }
    assert insights[1]["completed"] is False
    assert insights[1]["days_until_due"] == 3
    assert insights[1]["deadline_status"] == "Upcoming"
    assert insights[1]["priority"] == "Medium"


def test_insight_endpoint_is_read_only_and_crud_response_is_unchanged(
    prioritization_test_context: PrioritizationTestContext,
) -> None:
    """Insights must not mutate records or add fields to existing CRUD responses."""
    client, session_factory = prioritization_test_context
    add_insight_records(session_factory, date.today())

    with session_factory() as database_session:
        before = [
            (row.id, row.name, row.due, row.difficulty, row.completed)
            for row in database_session.scalars(select(Assignment).order_by(Assignment.id))
        ]

    insight_response = client.get("/assignments/insights")
    assignment_response = client.get("/assignments")

    with session_factory() as database_session:
        after = [
            (row.id, row.name, row.due, row.difficulty, row.completed)
            for row in database_session.scalars(select(Assignment).order_by(Assignment.id))
        ]

    assert insight_response.status_code == 200
    assert after == before
    assert assignment_response.status_code == 200
    assert set(assignment_response.json()[0]) == {
        "id",
        "name",
        "course_id",
        "due",
        "difficulty",
        "estimated_hours",
        "completed",
    }


def test_insight_endpoint_reports_invalid_stored_difficulty(
    prioritization_test_context: PrioritizationTestContext,
) -> None:
    """A legacy invalid value should receive a clear client error, not a priority."""
    client, session_factory = prioritization_test_context
    with session_factory() as database_session:
        course = Course(name="Software Engineering", code="ITSC 3155")
        database_session.add(
            Assignment(
                name="Unsupported difficulty",
                course=course,
                due=date.today(),
                difficulty="Urgent",
                estimated_hours=1,
                completed=False,
            )
        )
        database_session.commit()

    response = client.get("/assignments/insights")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Difficulty must be Low, Medium, or High."
    }
