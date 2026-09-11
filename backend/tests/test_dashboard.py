"""Tests for the read-only dashboard and workload summary."""

from collections.abc import Generator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables, get_db
from backend.app.main import app
from backend.app.models import Assignment, Course, Exam
from backend.app.services.workload import (
    build_dashboard_summary,
    calculate_workload_score,
    get_workload_level,
)

SessionFactory = sessionmaker[Session]
DashboardTestContext = tuple[TestClient, SessionFactory]


@pytest.fixture
def dashboard_test_context(
    tmp_path: Path,
) -> Generator[DashboardTestContext, None, None]:
    """Use a fresh temporary SQLite database for every dashboard test."""
    database_path = tmp_path / "ninerlife-dashboard-test.db"
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


def add_dashboard_records(
    session_factory: SessionFactory,
    today: date,
) -> None:
    """Add boundary, completed, overdue, and out-of-window test records."""
    with session_factory() as database_session:
        software = Course(name="Software Engineering", code="ITSC 3155")
        databases = Course(name="Database Design", code="ITSC 3160")
        database_session.add_all(
            [
                software,
                databases,
                Assignment(
                    name="Due today",
                    course=software,
                    due=today,
                    difficulty="High",
                    estimated_hours=2,
                    completed=False,
                ),
                Assignment(
                    name="Due on day seven",
                    course=databases,
                    due=today + timedelta(days=7),
                    difficulty="Medium",
                    estimated_hours=3,
                    completed=False,
                ),
                Assignment(
                    name="Outside assignment",
                    course=software,
                    due=today + timedelta(days=8),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=False,
                ),
                Assignment(
                    name="Completed assignment",
                    course=software,
                    due=today + timedelta(days=2),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=True,
                ),
                Assignment(
                    name="Overdue assignment",
                    course=databases,
                    due=today - timedelta(days=1),
                    difficulty="High",
                    estimated_hours=4,
                    completed=False,
                ),
                Assignment(
                    name="Completed overdue assignment",
                    course=databases,
                    due=today - timedelta(days=2),
                    difficulty="Medium",
                    estimated_hours=1,
                    completed=True,
                ),
                Exam(
                    name="Exam on day seven",
                    course=software,
                    exam_date=today + timedelta(days=7),
                    difficulty="High",
                    estimated_study_hours=5,
                    completed=False,
                ),
                Exam(
                    name="Outside exam",
                    course=databases,
                    exam_date=today + timedelta(days=8),
                    difficulty="Medium",
                    estimated_study_hours=3,
                    completed=False,
                ),
                Exam(
                    name="Completed exam",
                    course=databases,
                    exam_date=today + timedelta(days=3),
                    difficulty="Low",
                    estimated_study_hours=2,
                    completed=True,
                ),
            ]
        )
        database_session.commit()


def test_workload_formula_matches_v1() -> None:
    """The workload score should preserve all four original v1 weights."""
    assert calculate_workload_score(4, 3, 2, 12.5) == 67.5


@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (0, "Low"),
        (39.99, "Low"),
        (40, "Medium"),
        (69.99, "Medium"),
        (70, "High"),
    ],
)
def test_workload_level_thresholds(score: float, expected_level: str) -> None:
    """Low, Medium, and High boundaries should match NinerLife v1."""
    assert get_workload_level(score) == expected_level


def test_summary_includes_only_incomplete_records_in_inclusive_window(
    dashboard_test_context: DashboardTestContext,
) -> None:
    """Today and day seven count; completed and day-eight records do not."""
    client, session_factory = dashboard_test_context
    today = date.today()
    add_dashboard_records(session_factory, today)

    response = client.get("/dashboard/summary")
    summary = response.json()

    assert response.status_code == 200
    assert summary["total_course_count"] == 2
    assert summary["weekly_assignment_count"] == 2
    assert summary["weekly_exam_count"] == 1
    assert summary["overdue_incomplete_assignment_count"] == 1
    assert summary["work_hours"] == 0
    assert summary["workload_score"] == 30
    assert summary["workload_level"] == "Low"
    assert summary["window_start"] == today.isoformat()
    assert summary["window_end"] == (today + timedelta(days=7)).isoformat()
    assert [item["name"] for item in summary["upcoming_assignments"]] == [
        "Due today",
        "Due on day seven",
    ]
    assert summary["upcoming_assignments"][1]["course"] == {
        "id": 2,
        "name": "Database Design",
        "code": "ITSC 3160",
    }
    assert [item["name"] for item in summary["upcoming_exams"]] == [
        "Exam on day seven"
    ]
    assert summary["upcoming_exams"][0]["difficulty"] == "High"


def test_custom_work_hours_update_score(
    dashboard_test_context: DashboardTestContext,
) -> None:
    """A non-persisted work_hours query value should be included in the score."""
    client, session_factory = dashboard_test_context
    with session_factory() as database_session:
        database_session.add(Course(name="Software Engineering", code="ITSC 3155"))
        database_session.commit()

    response = client.get("/dashboard/summary", params={"work_hours": 35})

    assert response.status_code == 200
    assert response.json()["work_hours"] == 35
    assert response.json()["workload_score"] == 40
    assert response.json()["workload_level"] == "Medium"


def test_negative_work_hours_are_rejected(
    dashboard_test_context: DashboardTestContext,
) -> None:
    """FastAPI should return its normal validation response for negative hours."""
    client, _ = dashboard_test_context

    response = client.get("/dashboard/summary", params={"work_hours": -0.5})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "work_hours"


def test_build_summary_uses_injected_reference_date(
    dashboard_test_context: DashboardTestContext,
) -> None:
    """The service should support deterministic boundary testing directly."""
    _, session_factory = dashboard_test_context
    reference_date = date(2026, 9, 11)
    add_dashboard_records(session_factory, reference_date)

    with session_factory() as database_session:
        summary = build_dashboard_summary(
            database_session,
            work_hours=10,
            reference_date=reference_date,
        )

    assert summary.window_start == reference_date
    assert summary.window_end == date(2026, 9, 18)
    assert summary.weekly_assignment_count == 2
    assert summary.weekly_exam_count == 1
    assert summary.workload_score == 40
    assert summary.workload_level == "Medium"


def test_dashboard_endpoint_does_not_mutate_data(
    dashboard_test_context: DashboardTestContext,
) -> None:
    """Reading the dashboard must not insert, update, or delete any record."""
    client, session_factory = dashboard_test_context
    add_dashboard_records(session_factory, date.today())

    with session_factory() as database_session:
        before = (
            [(row.id, row.name, row.code) for row in database_session.scalars(select(Course))],
            [
                (row.id, row.name, row.due, row.completed)
                for row in database_session.scalars(select(Assignment))
            ],
            [
                (row.id, row.name, row.exam_date, row.completed)
                for row in database_session.scalars(select(Exam))
            ],
        )

    response = client.get("/dashboard/summary", params={"work_hours": 18})

    with session_factory() as database_session:
        after = (
            [(row.id, row.name, row.code) for row in database_session.scalars(select(Course))],
            [
                (row.id, row.name, row.due, row.completed)
                for row in database_session.scalars(select(Assignment))
            ],
            [
                (row.id, row.name, row.exam_date, row.completed)
                for row in database_session.scalars(select(Exam))
            ],
        )

    assert response.status_code == 200
    assert after == before
