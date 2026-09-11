"""API tests for Course CRUD operations."""

from collections.abc import Generator
from datetime import date
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
def course_api_context(tmp_path: Path) -> Generator[ApiTestContext, None, None]:
    """Use a fresh temporary database for each Course API test."""
    database_path = tmp_path / "ninerlife-course-api-test.db"
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


def course_payload(
    name: str = "Software Engineering",
    code: str = "ITSC 3155",
) -> dict[str, str]:
    """Return a valid Course request body."""
    return {"name": name, "code": code}


def create_course(client: TestClient, **changes: str) -> dict[str, object]:
    """Create and return a Course through the API."""
    payload = {**course_payload(), **changes}
    response = client.post("/courses", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_course(course_api_context: ApiTestContext) -> None:
    """POST should persist and return a valid Course."""
    client, session_factory = course_api_context

    response = client.post("/courses", json=course_payload())

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "Software Engineering",
        "code": "ITSC 3155",
    }
    with session_factory() as database_session:
        assert database_session.get(Course, 1) is not None


def test_get_all_courses(course_api_context: ApiTestContext) -> None:
    """GET collection should return Courses in ID order."""
    client, _ = course_api_context
    create_course(client)
    create_course(client, name="Database Design", code="ITSC 3160")

    response = client.get("/courses")

    assert response.status_code == 200
    assert [course["code"] for course in response.json()] == [
        "ITSC 3155",
        "ITSC 3160",
    ]


def test_get_one_course(course_api_context: ApiTestContext) -> None:
    """GET by ID should return the requested Course."""
    client, _ = course_api_context
    created_course = create_course(client)

    response = client.get(f"/courses/{created_course['id']}")

    assert response.status_code == 200
    assert response.json() == created_course


def test_update_course(course_api_context: ApiTestContext) -> None:
    """PUT should replace a Course's name and code."""
    client, _ = course_api_context
    created_course = create_course(client)
    updated_payload = course_payload(
        name="Software Engineering Studio",
        code="ITSC 4155",
    )

    response = client.put(
        f"/courses/{created_course['id']}",
        json=updated_payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": created_course["id"],
        **updated_payload,
    }


def test_delete_course_without_assignments(
    course_api_context: ApiTestContext,
) -> None:
    """DELETE should remove a Course that has no Assignments."""
    client, _ = course_api_context
    created_course = create_course(client)
    course_id = created_course["id"]

    delete_response = client.delete(f"/courses/{course_id}")
    get_response = client.get(f"/courses/{course_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404


def test_missing_course_returns_404(course_api_context: ApiTestContext) -> None:
    """Unknown Course IDs should receive a clear 404 response."""
    client, _ = course_api_context

    response = client.get("/courses/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Course with id 9999 was not found."}


def test_duplicate_code_on_create_is_rejected(
    course_api_context: ApiTestContext,
) -> None:
    """POST should reject a code already used with different casing."""
    client, _ = course_api_context
    create_course(client)

    response = client.post(
        "/courses",
        json=course_payload(name="Duplicate", code="  itsc 3155  "),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A Course with code 'itsc 3155' already exists."
    }
    assert len(client.get("/courses").json()) == 1


def test_duplicate_code_on_update_is_rejected(
    course_api_context: ApiTestContext,
) -> None:
    """PUT should not take another Course's normalized code."""
    client, _ = course_api_context
    first_course = create_course(client)
    second_course = create_course(client, name="Database Design", code="ITSC 3160")

    response = client.put(
        f"/courses/{second_course['id']}",
        json=course_payload(name="Duplicate", code="itsc 3155"),
    )
    unchanged_response = client.get(f"/courses/{second_course['id']}")

    assert response.status_code == 409
    assert unchanged_response.json() == second_course
    assert first_course["code"] == "ITSC 3155"


@pytest.mark.parametrize("field_name", ["name", "code"])
def test_blank_course_field_returns_422(
    field_name: str,
    course_api_context: ApiTestContext,
) -> None:
    """Required Course text fields should not accept blank values."""
    client, _ = course_api_context
    payload = {**course_payload(), field_name: "   "}

    response = client.post("/courses", json=payload)

    assert response.status_code == 422
    assert field_name in {
        error["loc"][-1] for error in response.json()["detail"]
    }


def test_unexpected_course_field_returns_422(
    course_api_context: ApiTestContext,
) -> None:
    """Course schemas should reject unexpected request fields."""
    client, _ = course_api_context

    response = client.post(
        "/courses",
        json={**course_payload(), "semester": "Fall 2026"},
    )

    assert response.status_code == 422


def test_delete_course_with_assignments_is_blocked(
    course_api_context: ApiTestContext,
) -> None:
    """DELETE should protect every Assignment linked to a Course."""
    client, session_factory = course_api_context
    created_course = create_course(client)
    course_id = int(created_course["id"])
    with session_factory.begin() as database_session:
        assignment = Assignment(
            name="Protected Assignment",
            course_id=course_id,
            due=date(2026, 9, 30),
            difficulty="High",
            estimated_hours=3.0,
            completed=False,
        )
        database_session.add(assignment)

    response = client.delete(f"/courses/{course_id}")

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            f"Course with id {course_id} cannot be deleted while it has "
            "Assignments. Remove or reassign them first."
        )
    }
    with session_factory() as database_session:
        assert database_session.get(Course, course_id) is not None
        assert database_session.get(Assignment, 1) is not None
