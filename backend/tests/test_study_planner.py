"""Tests for the deterministic, read-only NinerLife study planner."""

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
from backend.app.services.study_planner import (
    EXAM_TYPE_BONUS,
    build_study_plan,
    calculate_planner_score,
    get_difficulty_score,
    get_type_score,
    get_urgency_score,
)

SessionFactory = sessionmaker[Session]
StudyPlanTestContext = tuple[TestClient, SessionFactory]


@pytest.fixture
def study_plan_test_context(
    tmp_path: Path,
) -> Generator[StudyPlanTestContext, None, None]:
    """Use an isolated SQLite database for every study-plan test."""
    database_path = tmp_path / "ninerlife-study-plan-test.db"
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
    ("days_remaining", "expected_score"),
    [
        (-1, 60),
        (0, 50),
        (2, 50),
        (3, 35),
        (5, 35),
        (6, 20),
        (7, 20),
        (8, 10),
    ],
)
def test_urgency_score_boundaries(days_remaining: int, expected_score: int) -> None:
    """The centralized urgency score should preserve every documented boundary."""
    assert get_urgency_score(days_remaining) == expected_score


@pytest.mark.parametrize(
    ("difficulty", "expected_score"),
    [("Low", 5), ("mEdIuM", 10), (" HIGH ", 20)],
)
def test_difficulty_scores_are_normalized(
    difficulty: str,
    expected_score: int,
) -> None:
    """Difficulty contributions should use the existing canonical difficulty logic."""
    assert get_difficulty_score(difficulty) == expected_score


def test_exam_type_bonus_is_included() -> None:
    """Only exams should receive the fixed planner type bonus."""
    assert get_type_score("Assignment") == 0
    assert get_type_score("Exam") == EXAM_TYPE_BONUS
    assert calculate_planner_score(0, "High", "Exam") == 80
    assert calculate_planner_score(0, "High", "Assignment") == 70


def add_planner_records(session_factory: SessionFactory, today: date) -> None:
    """Seed all candidate, excluded, and allocation cases in a temporary database."""
    with session_factory() as database_session:
        software = Course(name="Software Engineering", code="ITSC 3155")
        databases = Course(name="Database Design", code="ITSC 3160")
        database_session.add_all(
            [
                software,
                databases,
                Assignment(
                    name="Overdue assignment",
                    course=software,
                    due=today - timedelta(days=1),
                    difficulty="High",
                    estimated_hours=2,
                    completed=False,
                ),
                Exam(
                    name="Today exam",
                    course=databases,
                    exam_date=today,
                    difficulty="High",
                    estimated_study_hours=3,
                    completed=False,
                ),
                Assignment(
                    name="Zero-hour assignment",
                    course=software,
                    due=today + timedelta(days=1),
                    difficulty="Low",
                    estimated_hours=0,
                    completed=False,
                ),
                Assignment(
                    name="Soon assignment",
                    course=databases,
                    due=today + timedelta(days=3),
                    difficulty="Medium",
                    estimated_hours=4,
                    completed=False,
                ),
                Assignment(
                    name="Completed assignment",
                    course=software,
                    due=today,
                    difficulty="High",
                    estimated_hours=5,
                    completed=True,
                ),
                Assignment(
                    name="Outside assignment",
                    course=software,
                    due=today + timedelta(days=8),
                    difficulty="High",
                    estimated_hours=1,
                    completed=False,
                ),
                Exam(
                    name="Completed exam",
                    course=databases,
                    exam_date=today + timedelta(days=1),
                    difficulty="High",
                    estimated_study_hours=2,
                    completed=True,
                ),
                Exam(
                    name="Outside exam",
                    course=databases,
                    exam_date=today + timedelta(days=8),
                    difficulty="High",
                    estimated_study_hours=2,
                    completed=False,
                ),
            ]
        )
        database_session.commit()


def test_planner_ranks_candidates_and_includes_course_data(
    study_plan_test_context: StudyPlanTestContext,
) -> None:
    """Overdue assignments and exams should be ranked deterministically with Course data."""
    _, session_factory = study_plan_test_context
    today = date(2026, 9, 11)
    add_planner_records(session_factory, today)

    with session_factory() as database_session:
        plan = build_study_plan(
            database_session,
            available_hours=10,
            horizon_days=7,
            reference_date=today,
        )

    assert [recommendation.name for recommendation in plan.recommendations] == [
        "Overdue assignment",
        "Today exam",
        "Zero-hour assignment",
        "Soon assignment",
    ]
    assert plan.recommendations[0].type == "Assignment"
    assert plan.recommendations[0].score == 80
    assert plan.recommendations[0].course.model_dump() == {
        "id": 1,
        "code": "ITSC 3155",
        "name": "Software Engineering",
    }
    assert plan.recommendations[0].reasons == [
        "Overdue assignment (+60)",
        "High difficulty (+20)",
    ]
    assert plan.recommendations[1].type == "Exam"
    assert plan.recommendations[1].score == 80
    assert plan.recommendations[1].reasons[-1] == "Exam (+10)"


def test_available_hours_allocation_handles_insufficient_excess_and_zero_estimates(
    study_plan_test_context: StudyPlanTestContext,
) -> None:
    """Allocation should be ordered, bounded, and preserve zero-hour items."""
    _, session_factory = study_plan_test_context
    today = date(2026, 9, 11)
    add_planner_records(session_factory, today)

    with session_factory() as database_session:
        limited_plan = build_study_plan(
            database_session,
            available_hours=5,
            horizon_days=7,
            reference_date=today,
        )
        excess_plan = build_study_plan(
            database_session,
            available_hours=20,
            horizon_days=7,
            reference_date=today,
        )

    assert [item.recommended_study_hours for item in limited_plan.recommendations] == [
        2,
        3,
        0,
        0,
    ]
    assert limited_plan.allocated_hours == 5
    assert limited_plan.remaining_hours == 0
    assert [item.recommended_study_hours for item in excess_plan.recommendations] == [
        2,
        3,
        0,
        4,
    ]
    assert excess_plan.allocated_hours == 9
    assert excess_plan.remaining_hours == 11


def test_tie_breaking_uses_date_then_stable_id_and_name(
    study_plan_test_context: StudyPlanTestContext,
) -> None:
    """Equally scored candidates should always be returned in a predictable order."""
    _, session_factory = study_plan_test_context
    today = date(2026, 9, 11)
    with session_factory() as database_session:
        course = Course(name="Software Engineering", code="ITSC 3155")
        database_session.add_all(
            [
                course,
                Assignment(
                    name="Zulu task",
                    course=course,
                    due=today + timedelta(days=4),
                    difficulty="High",
                    estimated_hours=1,
                    completed=False,
                ),
                Assignment(
                    name="Alpha task",
                    course=course,
                    due=today + timedelta(days=4),
                    difficulty="High",
                    estimated_hours=1,
                    completed=False,
                ),
            ]
        )
        database_session.commit()
        plan = build_study_plan(
            database_session,
            available_hours=4,
            horizon_days=7,
            reference_date=today,
        )

    assert [item.name for item in plan.recommendations] == ["Zulu task", "Alpha task"]


def test_endpoint_defaults_validation_and_read_only_behavior(
    study_plan_test_context: StudyPlanTestContext,
) -> None:
    """Endpoint defaults, invalid parameters, and reads should leave data untouched."""
    client, session_factory = study_plan_test_context
    add_planner_records(session_factory, date.today())

    with session_factory() as database_session:
        before = [
            (row.id, row.name, row.completed)
            for row in database_session.scalars(select(Assignment).order_by(Assignment.id))
        ]

    response = client.get("/study-plan")
    zero_hours = client.get("/study-plan", params={"available_hours": 0})
    negative_hours = client.get("/study-plan", params={"available_hours": -1})
    zero_horizon = client.get("/study-plan", params={"horizon_days": 0})
    long_horizon = client.get("/study-plan", params={"horizon_days": 31})

    with session_factory() as database_session:
        after = [
            (row.id, row.name, row.completed)
            for row in database_session.scalars(select(Assignment).order_by(Assignment.id))
        ]

    assert response.status_code == 200
    assert response.json()["available_hours"] == 4
    assert response.json()["horizon_days"] == 7
    assert response.json()["recommendations"][0]["course"] == {
        "id": 1,
        "code": "ITSC 3155",
        "name": "Software Engineering",
    }
    assert zero_hours.status_code == 422
    assert negative_hours.status_code == 422
    assert zero_horizon.status_code == 422
    assert long_horizon.status_code == 422
    assert after == before
