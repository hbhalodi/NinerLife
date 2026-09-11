"""Import the preserved NinerLife v1 CSV into the v2 database."""

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..database import SessionLocal, create_database_tables
from ..models import Assignment, Course

PROJECT_DIRECTORY = Path(__file__).resolve().parents[3]
DEFAULT_CSV_PATH = PROJECT_DIRECTORY / "assignments.csv"
REQUIRED_COLUMNS = {
    "name",
    "course",
    "due",
    "difficulty",
    "estimated_hours",
}

SessionFactory = sessionmaker[Session]


class CsvMigrationError(ValueError):
    """Raised when CSV data cannot be migrated safely."""


@dataclass(frozen=True)
class CsvAssignment:
    """One validated assignment from the v1 CSV."""

    row_number: int
    name: str
    course: str
    due: date
    difficulty: str
    estimated_hours: float


@dataclass(frozen=True)
class CoursePreview:
    """A planned Course creation or reuse action."""

    csv_value: str
    action: str
    course_id: int | None


@dataclass(frozen=True)
class AssignmentPreview:
    """A planned Assignment import or duplicate-skip action."""

    row_number: int
    name: str
    course: str
    due: date
    difficulty: str
    estimated_hours: float
    action: str


@dataclass(frozen=True)
class MigrationPreview:
    """Read-only plan for a v1 CSV migration."""

    total_rows: int
    courses: tuple[CoursePreview, ...]
    assignments: tuple[AssignmentPreview, ...]

    @property
    def assignments_to_import(self) -> int:
        return sum(item.action == "import" for item in self.assignments)

    @property
    def assignments_to_skip(self) -> int:
        return sum(item.action == "skip duplicate" for item in self.assignments)


@dataclass(frozen=True)
class MigrationResult:
    """Counts produced by a completed v1 CSV migration."""

    total_rows: int
    courses_created: int
    courses_reused: int
    assignments_imported: int
    assignments_skipped: int


def normalize_text(value: str) -> str:
    """Create a comparison key without changing the stored source value."""
    return " ".join(value.split()).casefold()


def required_text(row: dict[str, str], column: str, row_number: int) -> str:
    """Return required trimmed text or identify the invalid CSV row."""
    value = row.get(column)
    if value is None or not value.strip():
        raise CsvMigrationError(f"Row {row_number}: '{column}' must not be blank.")
    return value.strip()


def read_v1_csv(csv_path: Path) -> list[CsvAssignment]:
    """Read and validate every CSV row before any database write occurs."""
    try:
        csv_file = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise CsvMigrationError(f"Unable to open CSV file '{csv_path}': {error}") from error

    with csv_file:
        reader = csv.DictReader(csv_file)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_COLUMNS - columns)
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise CsvMigrationError(f"CSV is missing required columns: {missing}.")

        assignments: list[CsvAssignment] = []
        for row_number, row in enumerate(reader, start=2):
            name = required_text(row, "name", row_number)
            course = required_text(row, "course", row_number)
            due_text = required_text(row, "due", row_number)
            difficulty = required_text(row, "difficulty", row_number)
            hours_text = required_text(row, "estimated_hours", row_number)

            try:
                due = date.fromisoformat(due_text)
            except ValueError as error:
                raise CsvMigrationError(
                    f"Row {row_number}: invalid due date '{due_text}'; "
                    "expected YYYY-MM-DD."
                ) from error

            try:
                estimated_hours = float(hours_text)
            except ValueError as error:
                raise CsvMigrationError(
                    f"Row {row_number}: invalid estimated_hours '{hours_text}'."
                ) from error

            if not math.isfinite(estimated_hours) or estimated_hours < 0:
                raise CsvMigrationError(
                    f"Row {row_number}: estimated_hours must be a non-negative number."
                )

            assignments.append(
                CsvAssignment(
                    row_number=row_number,
                    name=name,
                    course=course,
                    due=due,
                    difficulty=difficulty,
                    estimated_hours=estimated_hours,
                )
            )

    return assignments


def build_course_index(courses: list[Course]) -> dict[str, dict[int, Course]]:
    """Index existing courses by normalized name and code."""
    course_index: dict[str, dict[int, Course]] = {}
    for course in courses:
        for value in {course.name, course.code}:
            key = normalize_text(value)
            course_index.setdefault(key, {})[course.id] = course
    return course_index


def find_matching_course(
    csv_course: str,
    course_index: dict[str, dict[int, Course]],
) -> Course | None:
    """Find one unambiguous Course matching a CSV course string."""
    matches = course_index.get(normalize_text(csv_course), {})
    if len(matches) > 1:
        matching_ids = ", ".join(str(course_id) for course_id in sorted(matches))
        raise CsvMigrationError(
            f"CSV course '{csv_course}' matches multiple Course rows: {matching_ids}."
        )
    return next(iter(matches.values()), None)


def assignment_signature(
    assignment_name: str,
    course_identity: tuple[str, int | str],
    due: date,
    difficulty: str,
    estimated_hours: float,
) -> tuple[object, ...]:
    """Build the natural key used to prevent duplicate imports."""
    return (
        normalize_text(assignment_name),
        course_identity,
        due,
        normalize_text(difficulty),
        estimated_hours,
    )


def preview_v1_csv(
    csv_path: Path = DEFAULT_CSV_PATH,
    session_factory: SessionFactory = SessionLocal,
) -> MigrationPreview:
    """Build a migration plan without writing to the database."""
    csv_assignments = read_v1_csv(csv_path)

    with session_factory() as database_session:
        existing_courses = list(database_session.scalars(select(Course)).all())
        course_index = build_course_index(existing_courses)
        existing_assignments = database_session.scalars(select(Assignment)).all()

        known_signatures = {
            assignment_signature(
                assignment.name,
                ("course_id", assignment.course_id),
                assignment.due,
                assignment.difficulty,
                assignment.estimated_hours,
            )
            for assignment in existing_assignments
        }

        course_plans: list[CoursePreview] = []
        course_matches: dict[str, Course | None] = {}
        for csv_assignment in csv_assignments:
            course_key = normalize_text(csv_assignment.course)
            if course_key in course_matches:
                continue

            matching_course = find_matching_course(csv_assignment.course, course_index)
            course_matches[course_key] = matching_course
            course_plans.append(
                CoursePreview(
                    csv_value=csv_assignment.course,
                    action="reuse" if matching_course else "create",
                    course_id=matching_course.id if matching_course else None,
                )
            )

        assignment_plans: list[AssignmentPreview] = []
        for csv_assignment in csv_assignments:
            course_key = normalize_text(csv_assignment.course)
            matching_course = course_matches[course_key]
            course_identity: tuple[str, int | str]
            if matching_course is None:
                course_identity = ("csv_course", course_key)
            else:
                course_identity = ("course_id", matching_course.id)

            signature = assignment_signature(
                csv_assignment.name,
                course_identity,
                csv_assignment.due,
                csv_assignment.difficulty,
                csv_assignment.estimated_hours,
            )
            action = "skip duplicate" if signature in known_signatures else "import"
            known_signatures.add(signature)
            assignment_plans.append(
                AssignmentPreview(
                    row_number=csv_assignment.row_number,
                    name=csv_assignment.name,
                    course=csv_assignment.course,
                    due=csv_assignment.due,
                    difficulty=csv_assignment.difficulty,
                    estimated_hours=csv_assignment.estimated_hours,
                    action=action,
                )
            )

    return MigrationPreview(
        total_rows=len(csv_assignments),
        courses=tuple(course_plans),
        assignments=tuple(assignment_plans),
    )


def import_v1_csv(
    csv_path: Path = DEFAULT_CSV_PATH,
    session_factory: SessionFactory = SessionLocal,
) -> MigrationResult:
    """Import all valid, non-duplicate rows in one database transaction."""
    csv_assignments = read_v1_csv(csv_path)
    courses_created = 0
    courses_reused = 0
    assignments_imported = 0
    assignments_skipped = 0

    with session_factory.begin() as database_session:
        existing_courses = list(database_session.scalars(select(Course)).all())
        course_index = build_course_index(existing_courses)
        course_matches: dict[str, Course] = {}

        for csv_assignment in csv_assignments:
            course_key = normalize_text(csv_assignment.course)
            if course_key in course_matches:
                continue

            course = find_matching_course(csv_assignment.course, course_index)
            if course is None:
                course = Course(
                    name=csv_assignment.course,
                    code=csv_assignment.course,
                )
                database_session.add(course)
                database_session.flush()
                course_index.setdefault(course_key, {})[course.id] = course
                courses_created += 1
            else:
                courses_reused += 1
            course_matches[course_key] = course

        existing_assignments = database_session.scalars(select(Assignment)).all()
        known_signatures = {
            assignment_signature(
                assignment.name,
                ("course_id", assignment.course_id),
                assignment.due,
                assignment.difficulty,
                assignment.estimated_hours,
            )
            for assignment in existing_assignments
        }

        for csv_assignment in csv_assignments:
            course = course_matches[normalize_text(csv_assignment.course)]
            signature = assignment_signature(
                csv_assignment.name,
                ("course_id", course.id),
                csv_assignment.due,
                csv_assignment.difficulty,
                csv_assignment.estimated_hours,
            )
            if signature in known_signatures:
                assignments_skipped += 1
                continue

            database_session.add(
                Assignment(
                    name=csv_assignment.name,
                    course_id=course.id,
                    due=csv_assignment.due,
                    difficulty=csv_assignment.difficulty,
                    estimated_hours=csv_assignment.estimated_hours,
                    completed=False,
                )
            )
            known_signatures.add(signature)
            assignments_imported += 1

    return MigrationResult(
        total_rows=len(csv_assignments),
        courses_created=courses_created,
        courses_reused=courses_reused,
        assignments_imported=assignments_imported,
        assignments_skipped=assignments_skipped,
    )


def print_preview(preview: MigrationPreview) -> None:
    """Print a readable dry-run plan for manual review."""
    print(f"CSV rows: {preview.total_rows}")
    print("Course plan:")
    for course in preview.courses:
        if course.action == "reuse":
            print(
                f"  {course.csv_value!r}: reuse Course id={course.course_id}"
            )
        else:
            print(
                f"  {course.csv_value!r}: create Course with "
                f"name={course.csv_value!r}, code={course.csv_value!r}"
            )

    print("Assignment plan:")
    for assignment in preview.assignments:
        print(
            f"  Row {assignment.row_number}: {assignment.action} "
            f"{assignment.name!r} -> course={assignment.course!r}, "
            f"due={assignment.due.isoformat()}, "
            f"difficulty={assignment.difficulty!r}, "
            f"estimated_hours={assignment.estimated_hours}, completed=False"
        )

    print(f"Assignments to import: {preview.assignments_to_import}")
    print(f"Assignments to skip: {preview.assignments_to_skip}")


def main() -> None:
    """Run a dry-run preview or the intentional v1 CSV import command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to the v1 assignments CSV file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the migration plan without changing the database.",
    )
    arguments = parser.parse_args()

    try:
        if arguments.dry_run:
            print_preview(preview_v1_csv(arguments.csv))
            return

        create_database_tables()
        result = import_v1_csv(arguments.csv)
    except CsvMigrationError as error:
        parser.exit(status=1, message=f"Migration failed: {error}\n")

    print("Migration completed successfully.")
    print(f"CSV rows: {result.total_rows}")
    print(f"Courses created: {result.courses_created}")
    print(f"Courses reused: {result.courses_reused}")
    print(f"Assignments imported: {result.assignments_imported}")
    print(f"Assignments skipped: {result.assignments_skipped}")


if __name__ == "__main__":
    main()
