"""Explicit, idempotent copy of local SQLite data into a PostgreSQL target."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..database import (
    DATABASE_PATH,
    create_database_engine,
    create_database_tables,
    normalize_database_url,
)
from ..models import Assignment, Course, Exam


class SQLiteCopyError(ValueError):
    """Raised when a requested SQLite-to-target copy is unsafe or incomplete."""


@dataclass(frozen=True)
class SQLiteCopySummary:
    """Counts from one explicit SQLite-to-target copy run."""

    courses_created: int = 0
    courses_reused: int = 0
    assignments_created: int = 0
    assignments_skipped: int = 0
    exams_created: int = 0
    exams_skipped: int = 0


def default_source_sqlite_url() -> str:
    """Return the preserved local NinerLife SQLite database URL."""
    return f"sqlite:///{DATABASE_PATH.as_posix()}"


def get_postgres_target_url(environ: Mapping[str, str] | None = None) -> str:
    """Require a PostgreSQL target from DATABASE_URL, never from a CLI argument."""
    environment = os.environ if environ is None else environ
    configured_url = environment.get("DATABASE_URL", "").strip()
    if not configured_url:
        raise SQLiteCopyError(
            "DATABASE_URL must be set to a PostgreSQL target before running this copy."
        )

    target_url = normalize_database_url(configured_url)
    if not target_url.startswith("postgresql+psycopg://"):
        raise SQLiteCopyError(
            "DATABASE_URL must point to PostgreSQL; the SQLite source is never a copy target."
        )

    return target_url


def normalized_course_code(code: str) -> str:
    """Match course codes consistently without changing stored values."""
    return " ".join(code.split()).casefold()


def assignment_key(assignment: Assignment, target_course_id: int) -> tuple[object, ...]:
    """Return a stable, data-preserving key for duplicate protection."""
    return (
        assignment.name,
        target_course_id,
        assignment.due,
        assignment.difficulty,
        assignment.estimated_hours,
        assignment.completed,
    )


def exam_key(exam: Exam, target_course_id: int) -> tuple[object, ...]:
    """Return a stable, data-preserving key for duplicate protection."""
    return (
        exam.name,
        target_course_id,
        exam.exam_date,
        exam.difficulty,
        exam.estimated_study_hours,
        exam.completed,
    )


def matching_assignment_count(
    database_session: Session,
    key: tuple[object, ...],
) -> int:
    """Count target Assignments with the same copied data."""
    name, course_id, due, difficulty, estimated_hours, completed = key
    return len(
        database_session.scalars(
            select(Assignment.id).where(
                Assignment.name == name,
                Assignment.course_id == course_id,
                Assignment.due == due,
                Assignment.difficulty == difficulty,
                Assignment.estimated_hours == estimated_hours,
                Assignment.completed.is_(completed),
            )
        ).all()
    )


def matching_exam_count(
    database_session: Session,
    key: tuple[object, ...],
) -> int:
    """Count target Exams with the same copied data."""
    name, course_id, exam_date, difficulty, estimated_study_hours, completed = key
    return len(
        database_session.scalars(
            select(Exam.id).where(
                Exam.name == name,
                Exam.course_id == course_id,
                Exam.exam_date == exam_date,
                Exam.difficulty == difficulty,
                Exam.estimated_study_hours == estimated_study_hours,
                Exam.completed.is_(completed),
            )
        ).all()
    )


def copy_sqlite_data(source_engine: Engine, target_engine: Engine) -> SQLiteCopySummary:
    """Copy source data once while preserving relationships and duplicate safety.

    The source engine is only read. Target inserts occur in one transaction, so
    validation or insert failures roll back all copied application records.
    """
    if source_engine.url.get_backend_name() != "sqlite":
        raise SQLiteCopyError("The source database must be SQLite.")

    create_database_tables(target_engine)
    source_session_factory = sessionmaker(bind=source_engine, expire_on_commit=False)
    target_session_factory = sessionmaker(bind=target_engine, expire_on_commit=False)

    with source_session_factory() as source_session:
        source_courses = list(source_session.scalars(select(Course).order_by(Course.id)))
        source_assignments = list(
            source_session.scalars(select(Assignment).order_by(Assignment.id))
        )
        source_exams = list(source_session.scalars(select(Exam).order_by(Exam.id)))

        with target_session_factory() as target_session:
            with target_session.begin():
                target_courses = list(target_session.scalars(select(Course)))
                courses_by_code = {
                    normalized_course_code(course.code): course for course in target_courses
                }
                target_course_ids: dict[int, int] = {}
                courses_created = 0
                courses_reused = 0

                for source_course in source_courses:
                    normalized_code = normalized_course_code(source_course.code)
                    target_course = courses_by_code.get(normalized_code)
                    if target_course is not None:
                        if target_course.name != source_course.name:
                            raise SQLiteCopyError(
                                "A target Course uses code "
                                f"'{source_course.code}' with a different name."
                            )
                        courses_reused += 1
                    else:
                        target_course = Course(
                            name=source_course.name,
                            code=source_course.code,
                        )
                        target_session.add(target_course)
                        target_session.flush()
                        courses_by_code[normalized_code] = target_course
                        courses_created += 1

                    target_course_ids[source_course.id] = target_course.id

                seen_assignments: defaultdict[tuple[object, ...], int] = defaultdict(int)
                assignments_created = 0
                assignments_skipped = 0
                for source_assignment in source_assignments:
                    target_course_id = target_course_ids.get(source_assignment.course_id)
                    if target_course_id is None:
                        raise SQLiteCopyError(
                            f"Assignment '{source_assignment.name}' has no source Course."
                        )

                    key = assignment_key(source_assignment, target_course_id)
                    existing_count = matching_assignment_count(target_session, key)
                    if existing_count > seen_assignments[key]:
                        assignments_skipped += 1
                    else:
                        target_session.add(
                            Assignment(
                                name=source_assignment.name,
                                course_id=target_course_id,
                                due=source_assignment.due,
                                difficulty=source_assignment.difficulty,
                                estimated_hours=source_assignment.estimated_hours,
                                completed=source_assignment.completed,
                            )
                        )
                        assignments_created += 1
                    seen_assignments[key] += 1

                seen_exams: defaultdict[tuple[object, ...], int] = defaultdict(int)
                exams_created = 0
                exams_skipped = 0
                for source_exam in source_exams:
                    target_course_id = target_course_ids.get(source_exam.course_id)
                    if target_course_id is None:
                        raise SQLiteCopyError(
                            f"Exam '{source_exam.name}' has no source Course."
                        )

                    key = exam_key(source_exam, target_course_id)
                    existing_count = matching_exam_count(target_session, key)
                    if existing_count > seen_exams[key]:
                        exams_skipped += 1
                    else:
                        target_session.add(
                            Exam(
                                name=source_exam.name,
                                course_id=target_course_id,
                                exam_date=source_exam.exam_date,
                                difficulty=source_exam.difficulty,
                                estimated_study_hours=source_exam.estimated_study_hours,
                                completed=source_exam.completed,
                            )
                        )
                        exams_created += 1
                    seen_exams[key] += 1

    return SQLiteCopySummary(
        courses_created=courses_created,
        courses_reused=courses_reused,
        assignments_created=assignments_created,
        assignments_skipped=assignments_skipped,
        exams_created=exams_created,
        exams_skipped=exams_skipped,
    )


def main() -> None:
    """Run an intentional copy from the preserved local SQLite database."""
    parser = argparse.ArgumentParser(
        description="Copy NinerLife SQLite data into the PostgreSQL DATABASE_URL target."
    )
    parser.add_argument(
        "--source-sqlite-path",
        type=Path,
        default=DATABASE_PATH,
        help="Optional source SQLite path; defaults to backend/ninerlife.db.",
    )
    arguments = parser.parse_args()
    source_path = arguments.source_sqlite_path.resolve()

    if not source_path.is_file():
        raise SystemExit(f"SQLite source database was not found: {source_path}")

    target_url = get_postgres_target_url()
    source_engine = create_engine(f"sqlite:///{source_path.as_posix()}")
    target_engine = create_database_engine(target_url)

    try:
        summary = copy_sqlite_data(source_engine, target_engine)
    finally:
        source_engine.dispose()
        target_engine.dispose()

    print("SQLite to PostgreSQL copy completed safely.")
    print(f"Courses: {summary.courses_created} created, {summary.courses_reused} reused")
    print(
        "Assignments: "
        f"{summary.assignments_created} created, {summary.assignments_skipped} skipped"
    )
    print(f"Exams: {summary.exams_created} created, {summary.exams_skipped} skipped")


if __name__ == "__main__":
    main()
