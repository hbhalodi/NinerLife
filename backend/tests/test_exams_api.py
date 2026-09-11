"""API tests for Exam CRUD operations."""

from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import create_database_tables, get_db
from backend.app.main import app
from backend.app.models import Exam, Course

SessionFactory = sessionmaker[Session]
ApiTestContext = tuple[TestClient, SessionFactory]


@pytest.fixture
def exam_api_context(tmp_path: Path) -> Generator[ApiTestContext, None, None]:
    """Use a fresh temporary database for each Exam API test."""
    database_path = tmp_path / "ninerlife-exam-api-test.db"
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
    name: str = "Operating Systems",
    code: str = "ITSC 3146",
) -> int:
    """Insert a Course directly for an Exam API test."""
    with session_factory() as database_session:
        course = Course(name=name, code=code)
        database_session.add(course)
        database_session.commit()
        database_session.refresh(course)
        return course.id


def exam_payload(course_id: int) -> dict[str, object]:
    """Return a valid Exam request body."""
    return {
        "name": "Midterm Exam",
        "course_id": course_id,
        "exam_date": "2026-10-10",
        "difficulty": "High",
        "estimated_study_hours": 8.0,
        "completed": False,
    }


def create_exam(
    client: TestClient,
    session_factory: SessionFactory,
) -> dict[str, object]:
    """Create and return an Exam through the API."""
    course_id = create_course(session_factory)
    response = client.post("/exams", json=exam_payload(course_id))
    assert response.status_code == 201
    return response.json()


def test_exam_table_is_created(exam_api_context: ApiTestContext) -> None:
    """Temporary database setup should include the Exams table."""
    _, session_factory = exam_api_context
    with session_factory() as database_session:
        assert "exams" in inspect(database_session.bind).get_table_names()


def test_create_exam(exam_api_context: ApiTestContext) -> None:
    """POST should persist and return a valid Exam."""
    client, session_factory = exam_api_context
    course_id = create_course(session_factory)

    response = client.post("/exams", json=exam_payload(course_id))

    assert response.status_code == 201
    assert response.json() == {"id": 1, **exam_payload(course_id)}
    with session_factory() as database_session:
        assert database_session.get(Exam, 1) is not None


def test_get_all_exams(exam_api_context: ApiTestContext) -> None:
    """GET collection should return Exams in ID order."""
    client, session_factory = exam_api_context
    course_id = create_course(session_factory)
    first_payload = exam_payload(course_id)
    second_payload = {
        **first_payload,
        "name": "Final Exam",
        "exam_date": "2026-12-10",
    }
    client.post("/exams", json=first_payload)
    client.post("/exams", json=second_payload)

    response = client.get("/exams")

    assert response.status_code == 200
    assert [exam["name"] for exam in response.json()] == [
        "Midterm Exam",
        "Final Exam",
    ]


def test_get_one_exam(exam_api_context: ApiTestContext) -> None:
    """GET by ID should return the requested Exam."""
    client, session_factory = exam_api_context
    created_exam = create_exam(client, session_factory)

    response = client.get(f"/exams/{created_exam['id']}")

    assert response.status_code == 200
    assert response.json() == created_exam


def test_update_exam(exam_api_context: ApiTestContext) -> None:
    """PUT should replace fields and allow changing the related Course."""
    client, session_factory = exam_api_context
    created_exam = create_exam(client, session_factory)
    new_course_id = create_course(
        session_factory,
        name="Database Design",
        code="ITSC 3160",
    )
    updated_payload = {
        "name": "Final Exam",
        "course_id": new_course_id,
        "exam_date": "2026-12-10",
        "difficulty": "Medium",
        "estimated_study_hours": 6.5,
        "completed": True,
    }

    response = client.put(
        f"/exams/{created_exam['id']}",
        json=updated_payload,
    )

    assert response.status_code == 200
    assert response.json() == {"id": created_exam["id"], **updated_payload}


def test_delete_exam(exam_api_context: ApiTestContext) -> None:
    """DELETE should remove an Exam and return no content."""
    client, session_factory = exam_api_context
    created_exam = create_exam(client, session_factory)
    exam_id = created_exam["id"]

    delete_response = client.delete(f"/exams/{exam_id}")
    get_response = client.get(f"/exams/{exam_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404


def test_missing_exam_returns_404(exam_api_context: ApiTestContext) -> None:
    """Unknown Exam IDs should receive a clear 404 response."""
    client, _ = exam_api_context

    response = client.get("/exams/9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exam with id 9999 was not found."}


def test_create_rejects_unknown_course(exam_api_context: ApiTestContext) -> None:
    """POST should not persist an Exam for an unknown Course."""
    client, _ = exam_api_context

    response = client.post("/exams", json=exam_payload(9999))

    assert response.status_code == 404
    assert response.json() == {"detail": "Course with id 9999 was not found."}
    assert client.get("/exams").json() == []


def test_update_rejects_unknown_course(exam_api_context: ApiTestContext) -> None:
    """PUT should leave an Exam unchanged if its Course is unknown."""
    client, session_factory = exam_api_context
    created_exam = create_exam(client, session_factory)
    invalid_payload = {
        **exam_payload(9999),
        "name": "This update must not be saved",
    }

    response = client.put(
        f"/exams/{created_exam['id']}",
        json=invalid_payload,
    )
    unchanged_response = client.get(f"/exams/{created_exam['id']}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Course with id 9999 was not found."}
    assert unchanged_response.json() == created_exam


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("name", "   "),
        ("course_id", 0),
        ("exam_date", "not-a-date"),
        ("difficulty", "   "),
        ("estimated_study_hours", -1),
        ("completed", "not-a-boolean"),
    ],
)
def test_invalid_exam_data_returns_422(
    field_name: str,
    invalid_value: object,
    exam_api_context: ApiTestContext,
) -> None:
    """Pydantic should reject each invalid Exam field value."""
    client, session_factory = exam_api_context
    course_id = create_course(session_factory)
    payload = {**exam_payload(course_id), field_name: invalid_value}

    response = client.post("/exams", json=payload)

    assert response.status_code == 422
    assert field_name in {
        error["loc"][-1] for error in response.json()["detail"]
    }


def test_unexpected_exam_field_returns_422(
    exam_api_context: ApiTestContext,
) -> None:
    """Exam schemas should reject unexpected request fields."""
    client, session_factory = exam_api_context
    course_id = create_course(session_factory)

    response = client.post(
        "/exams",
        json={**exam_payload(course_id), "notes": "Not in Phase 6"},
    )

    assert response.status_code == 422


def test_course_exams_relationship(exam_api_context: ApiTestContext) -> None:
    """Course.exams and Exam.course should reference each other."""
    _, session_factory = exam_api_context
    with session_factory.begin() as database_session:
        course = Course(name="Data Structures", code="ITSC 2214")
        exam = Exam(
            name="Final Exam",
            course=course,
            exam_date=date(2026, 12, 10),
            difficulty="High",
            estimated_study_hours=10.0,
            completed=False,
        )
        database_session.add(exam)

    with session_factory() as database_session:
        saved_exam = database_session.get(Exam, 1)
        assert saved_exam is not None
        assert saved_exam.course.exams == [saved_exam]


def test_course_with_exam_cannot_be_deleted(
    exam_api_context: ApiTestContext,
) -> None:
    """Course DELETE should not cascade-delete a linked Exam."""
    client, session_factory = exam_api_context
    created_exam = create_exam(client, session_factory)
    course_id = created_exam["course_id"]

    response = client.delete(f"/courses/{course_id}")

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            f"Course with id {course_id} cannot be deleted while it has "
            "Exams. Remove or reassign them first."
        )
    }
    assert client.get(f"/exams/{created_exam['id']}").status_code == 200
