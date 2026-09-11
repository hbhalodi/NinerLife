"""API tests for assignment CRUD operations."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables, get_db
from backend.app.main import app
from backend.app.models import Assignment, Course

SessionFactory = sessionmaker[Session]
ApiTestContext = tuple[TestClient, SessionFactory]


@pytest.fixture
def api_test_context(tmp_path: Path) -> Generator[ApiTestContext, None, None]:
    """Use a fresh temporary database for each API test."""
    database_path = tmp_path / "ninerlife-api-test.db"
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


def create_course(
    session_factory: SessionFactory,
    name: str = "Software Engineering",
    code: str = "ITSC 3155",
) -> int:
    """Insert a Course directly because Course CRUD is a later phase."""
    with session_factory() as database_session:
        course = Course(name=name, code=code)
        database_session.add(course)
        database_session.commit()
        database_session.refresh(course)
        return course.id


def assignment_payload(course_id: int) -> dict[str, object]:
    """Return a valid assignment request body."""
    return {
        "name": "Build Assignment API",
        "course_id": course_id,
        "due": "2026-09-20",
        "difficulty": "High",
        "estimated_hours": 5.0,
        "completed": False,
    }


def create_assignment(
    client: TestClient,
    session_factory: SessionFactory,
) -> dict[str, object]:
    """Create and return an assignment through the API."""
    course_id = create_course(session_factory)
    response = client.post("/assignments", json=assignment_payload(course_id))
    assert response.status_code == 201
    return response.json()


def test_create_assignment(api_test_context: ApiTestContext) -> None:
    """POST should persist and return a valid assignment."""
    client, session_factory = api_test_context
    course_id = create_course(session_factory)

    response = client.post("/assignments", json=assignment_payload(course_id))

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        **assignment_payload(course_id),
    }
    with session_factory() as database_session:
        assert database_session.get(Assignment, 1) is not None


def test_get_all_assignments(api_test_context: ApiTestContext) -> None:
    """GET collection should return every assignment in ID order."""
    client, session_factory = api_test_context
    course_id = create_course(session_factory)
    first_payload = assignment_payload(course_id)
    second_payload = {
        **first_payload,
        "name": "Test Assignment API",
        "due": "2026-09-21",
    }
    client.post("/assignments", json=first_payload)
    client.post("/assignments", json=second_payload)

    response = client.get("/assignments")

    assert response.status_code == 200
    assert [assignment["name"] for assignment in response.json()] == [
        "Build Assignment API",
        "Test Assignment API",
    ]


def test_get_one_assignment(api_test_context: ApiTestContext) -> None:
    """GET by ID should return the requested assignment."""
    client, session_factory = api_test_context
    created_assignment = create_assignment(client, session_factory)

    response = client.get(f"/assignments/{created_assignment['id']}")

    assert response.status_code == 200
    assert response.json() == created_assignment


def test_update_assignment(api_test_context: ApiTestContext) -> None:
    """PUT should replace fields and allow changing the related course."""
    client, session_factory = api_test_context
    created_assignment = create_assignment(client, session_factory)
    new_course_id = create_course(
        session_factory,
        name="Database Design",
        code="ITSC 3160",
    )
    updated_payload = {
        "name": "Complete Assignment API",
        "course_id": new_course_id,
        "due": "2026-09-22",
        "difficulty": "Medium",
        "estimated_hours": 2.5,
        "completed": True,
    }

    response = client.put(
        f"/assignments/{created_assignment['id']}",
        json=updated_payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": created_assignment["id"],
        **updated_payload,
    }


def test_delete_assignment(api_test_context: ApiTestContext) -> None:
    """DELETE should remove an assignment and return no content."""
    client, session_factory = api_test_context
    created_assignment = create_assignment(client, session_factory)
    assignment_id = created_assignment["id"]

    delete_response = client.delete(f"/assignments/{assignment_id}")
    get_response = client.get(f"/assignments/{assignment_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404


def test_missing_assignment_returns_404(api_test_context: ApiTestContext) -> None:
    """Unknown assignment IDs should receive a clear 404 response."""
    client, _ = api_test_context

    response = client.get("/assignments/9999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Assignment with id 9999 was not found."
    }


def test_create_rejects_unknown_course(api_test_context: ApiTestContext) -> None:
    """POST should not persist an assignment for an unknown course."""
    client, _ = api_test_context

    response = client.post("/assignments", json=assignment_payload(9999))

    assert response.status_code == 404
    assert response.json() == {"detail": "Course with id 9999 was not found."}
    assert client.get("/assignments").json() == []


def test_update_rejects_unknown_course(api_test_context: ApiTestContext) -> None:
    """PUT should leave an assignment unchanged if its course is unknown."""
    client, session_factory = api_test_context
    created_assignment = create_assignment(client, session_factory)
    invalid_payload = {
        **assignment_payload(9999),
        "name": "This update must not be saved",
    }

    response = client.put(
        f"/assignments/{created_assignment['id']}",
        json=invalid_payload,
    )
    unchanged_response = client.get(f"/assignments/{created_assignment['id']}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Course with id 9999 was not found."}
    assert unchanged_response.json() == created_assignment


def test_invalid_assignment_data_returns_422(
    api_test_context: ApiTestContext,
) -> None:
    """Pydantic should reject missing, malformed, and invalid field values."""
    client, _ = api_test_context
    invalid_payload = {
        "name": "   ",
        "due": "not-a-date",
        "difficulty": "   ",
        "estimated_hours": -1,
        "completed": "not-a-boolean",
    }

    response = client.post("/assignments", json=invalid_payload)
    invalid_fields = {error["loc"][-1] for error in response.json()["detail"]}

    assert response.status_code == 422
    assert {
        "name",
        "course_id",
        "due",
        "difficulty",
        "estimated_hours",
        "completed",
    } <= invalid_fields
