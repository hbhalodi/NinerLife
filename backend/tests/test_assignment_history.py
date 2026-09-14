"""Tests for Assignment completion timestamps and seven-day history retention."""

from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables, get_db
from backend.app.main import app
from backend.app.migrations.add_assignment_completed_at import (
    CompletionTimestampMigrationError,
    completed_at_column_type,
    get_migration_database_url,
    migrate_assignment_completed_at,
)
from backend.app.models import Assignment, Course
from backend.app.services.assignment_history import (
    ASSIGNMENT_HISTORY_RETENTION_DAYS,
    purge_expired_assignment_history,
)
import backend.app.services.assignment_history as assignment_history

SessionFactory = sessionmaker[Session]
HistoryTestContext = tuple[TestClient, SessionFactory]


@pytest.fixture
def history_test_context(tmp_path: Path) -> Generator[HistoryTestContext, None, None]:
    """Use a fresh temporary SQLite database for each history test."""
    database_path = tmp_path / "ninerlife-history-test.db"
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


def assignment_payload(course_id: int, *, completed: bool = False) -> dict[str, object]:
    """Return a valid assignment payload for history behavior tests."""
    return {
        "name": "History verification assignment",
        "course_id": course_id,
        "due": "2026-10-01",
        "difficulty": "Medium",
        "estimated_hours": 2.0,
        "completed": completed,
    }


def create_course(session_factory: SessionFactory) -> int:
    """Insert one Course directly for an Assignment API relationship."""
    with session_factory() as database_session:
        course = Course(name="History Verification", code="HIST-TEST")
        database_session.add(course)
        database_session.commit()
        database_session.refresh(course)
        return course.id


def as_utc(timestamp: datetime) -> datetime:
    """Normalize SQLite's timezone-naive timestamp reads for assertions."""
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def test_api_completion_and_reopen_manage_completion_timestamp(
    history_test_context: HistoryTestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared API update path timestamps completion and clears reopening."""
    client, session_factory = history_test_context
    course_id = create_course(session_factory)
    created = client.post("/assignments", json=assignment_payload(course_id))
    assignment_id = created.json()["id"]
    completed_at = datetime(2026, 9, 13, 15, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(
        assignment_history,
        "current_utc_datetime",
        lambda: completed_at,
    )

    complete_response = client.put(
        f"/assignments/{assignment_id}",
        json=assignment_payload(course_id, completed=True),
    )

    assert complete_response.status_code == 200
    with session_factory() as database_session:
        saved_assignment = database_session.get(Assignment, assignment_id)
        assert saved_assignment is not None
        assert saved_assignment.completed is True
        assert saved_assignment.completed_at is not None
        assert as_utc(saved_assignment.completed_at) == completed_at

    reopen_response = client.put(
        f"/assignments/{assignment_id}",
        json=assignment_payload(course_id, completed=False),
    )

    assert reopen_response.status_code == 200
    with session_factory() as database_session:
        reopened_assignment = database_session.get(Assignment, assignment_id)
        assert reopened_assignment is not None
        assert reopened_assignment.completed is False
        assert reopened_assignment.completed_at is None


def test_api_create_completed_assignment_starts_a_fresh_history_window(
    history_test_context: HistoryTestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct API create marked complete cannot create timestamp-less history."""
    client, session_factory = history_test_context
    course_id = create_course(session_factory)
    completed_at = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        assignment_history,
        "current_utc_datetime",
        lambda: completed_at,
    )

    response = client.post("/assignments", json=assignment_payload(course_id, completed=True))

    assert response.status_code == 201
    with session_factory() as database_session:
        assignment = database_session.get(Assignment, response.json()["id"])
        assert assignment is not None
        assert assignment.completed_at is not None
        assert as_utc(assignment.completed_at) == completed_at


def test_purge_removes_only_completed_assignments_at_or_after_the_cutoff(
    history_test_context: HistoryTestContext,
) -> None:
    """The central purge keeps recent, incomplete, and legacy rows untouched."""
    _, session_factory = history_test_context
    now = datetime(2026, 9, 13, 12, tzinfo=timezone.utc)

    with session_factory() as database_session:
        course = Course(name="Retention Test", code="RET-TEST")
        database_session.add(course)
        database_session.flush()
        database_session.add_all(
            [
                Assignment(
                    name="At the cutoff",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=True,
                    completed_at=now - timedelta(days=ASSIGNMENT_HISTORY_RETENTION_DAYS),
                ),
                Assignment(
                    name="Older than the cutoff",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=True,
                    completed_at=now - timedelta(days=8),
                ),
                Assignment(
                    name="Recent completed work",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=True,
                    completed_at=now - timedelta(days=6),
                ),
                Assignment(
                    name="Legacy completed work",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=True,
                ),
                Assignment(
                    name="Incomplete work",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=False,
                ),
            ]
        )
        database_session.commit()

    with session_factory() as database_session:
        deleted_count = purge_expired_assignment_history(database_session, now=now)

    assert deleted_count == 2
    with session_factory() as database_session:
        remaining_names = set(database_session.scalars(select(Assignment.name)).all())
    assert remaining_names == {
        "Recent completed work",
        "Legacy completed work",
        "Incomplete work",
    }


def test_assignment_reads_purge_expired_history_without_touching_current_work(
    history_test_context: HistoryTestContext,
) -> None:
    """Relevant Assignment reads trigger retention cleanup before serialization."""
    client, session_factory = history_test_context
    expired_timestamp = datetime.now(timezone.utc) - timedelta(days=8)

    with session_factory() as database_session:
        course = Course(name="Read Cleanup", code="READ-CLEANUP")
        database_session.add(course)
        database_session.flush()
        database_session.add_all(
            [
                Assignment(
                    name="Expired history",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Low",
                    estimated_hours=1,
                    completed=True,
                    completed_at=expired_timestamp,
                ),
                Assignment(
                    name="Current work",
                    course_id=course.id,
                    due=date(2026, 10, 1),
                    difficulty="Medium",
                    estimated_hours=2,
                    completed=False,
                ),
            ]
        )
        database_session.commit()

    response = client.get("/assignments/insights")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Current work"]
    with session_factory() as database_session:
        assert database_session.scalar(
            select(Assignment).where(Assignment.name == "Expired history")
        ) is None
        assert database_session.scalar(
            select(Assignment).where(Assignment.name == "Current work")
        ) is not None


def test_dashboard_and_study_plan_exclude_freshly_completed_assignments(
    history_test_context: HistoryTestContext,
) -> None:
    """Completion immediately removes work from active summaries before retention ends."""
    client, session_factory = history_test_context
    today = date.today()

    with session_factory() as database_session:
        course = Course(name="Summary Exclusion", code="SUMMARY-EXCLUDE")
        database_session.add(course)
        database_session.flush()
        database_session.add_all(
            [
                Assignment(
                    name="Fresh completed work",
                    course_id=course.id,
                    due=today + timedelta(days=1),
                    difficulty="High",
                    estimated_hours=3,
                    completed=True,
                    completed_at=datetime.now(timezone.utc),
                ),
                Assignment(
                    name="Current scheduled work",
                    course_id=course.id,
                    due=today + timedelta(days=1),
                    difficulty="Medium",
                    estimated_hours=2,
                    completed=False,
                ),
            ]
        )
        database_session.commit()

    dashboard_response = client.get("/dashboard/summary")
    study_plan_response = client.get("/study-plan", params={"horizon_days": 7})

    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["weekly_assignment_count"] == 1
    assert [item["name"] for item in dashboard_response.json()["upcoming_assignments"]] == [
        "Current scheduled work"
    ]
    assert study_plan_response.status_code == 200
    assert [item["name"] for item in study_plan_response.json()["recommendations"]] == [
        "Current scheduled work"
    ]


def create_legacy_assignment_schema(database_engine: Engine) -> None:
    """Build the pre-completed_at SQLite schema used by the explicit migration."""
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE courses ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(200) NOT NULL, "
                "code VARCHAR(50) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE assignments ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(200) NOT NULL, "
                "course_id INTEGER NOT NULL, "
                "due DATE NOT NULL, "
                "difficulty VARCHAR(20) NOT NULL, "
                "estimated_hours FLOAT NOT NULL, "
                "completed BOOLEAN NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO courses (id, name, code) VALUES (1, 'Legacy', 'LEGACY')")
        )
        connection.execute(
            text(
                "INSERT INTO assignments "
                "(id, name, course_id, due, difficulty, estimated_hours, completed) "
                "VALUES (1, 'Legacy completed', 1, '2026-10-01', 'Low', 1, 1), "
                "(2, 'Legacy current', 1, '2026-10-01', 'Low', 1, 0)"
            )
        )


def test_completion_timestamp_migration_adds_and_backfills_idempotently(
    tmp_path: Path,
) -> None:
    """Legacy completed rows receive one fresh seven-day retention window."""
    database_engine = create_engine(
        f"sqlite:///{(tmp_path / 'legacy-history.db').as_posix()}"
    )
    backfill_time = datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc)
    create_legacy_assignment_schema(database_engine)

    first_result = migrate_assignment_completed_at(database_engine, now=backfill_time)
    second_result = migrate_assignment_completed_at(
        database_engine,
        now=backfill_time + timedelta(days=1),
    )

    assert first_result.column_added is True
    assert first_result.assignments_backfilled == 1
    assert second_result.column_added is False
    assert second_result.assignments_backfilled == 0
    assert "completed_at" in {
        column["name"] for column in inspect(database_engine).get_columns("assignments")
    }
    with sessionmaker(bind=database_engine)() as database_session:
        completed_assignment = database_session.get(Assignment, 1)
        current_assignment = database_session.get(Assignment, 2)
        assert completed_assignment is not None
        assert completed_assignment.completed_at is not None
        assert as_utc(completed_assignment.completed_at) == backfill_time
        assert current_assignment is not None
        assert current_assignment.completed_at is None

    database_engine.dispose()


def test_completion_timestamp_migration_target_selection_is_explicit() -> None:
    """The migration requires an environment target or deliberate local opt-in."""
    assert get_migration_database_url({}, use_local_sqlite=True).startswith("sqlite:///")
    assert get_migration_database_url(
        {"DATABASE_URL": "postgres://student:secret@db.example/ninerlife"}
    ) == "postgresql+psycopg://student:secret@db.example/ninerlife"
    assert completed_at_column_type("sqlite") == "DATETIME"
    assert completed_at_column_type("postgresql") == "TIMESTAMP WITH TIME ZONE"
    with pytest.raises(CompletionTimestampMigrationError, match="DATABASE_URL"):
        get_migration_database_url({})
