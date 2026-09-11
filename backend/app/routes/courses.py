"""REST API routes for course management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Assignment, Course, Exam
from ..schemas import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"])


def get_course_or_404(course_id: int, database_session: Session) -> Course:
    """Return a course or raise a clear not-found response."""
    course = database_session.get(Course, course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} was not found.",
        )
    return course


def normalize_course_code(code: str) -> str:
    """Normalize a code only for duplicate comparisons."""
    return " ".join(code.split()).casefold()


def find_course_with_code(
    code: str,
    database_session: Session,
    excluded_course_id: int | None = None,
) -> Course | None:
    """Find another Course with the same normalized code."""
    normalized_code = normalize_course_code(code)
    courses = database_session.scalars(select(Course)).all()
    return next(
        (
            course
            for course in courses
            if course.id != excluded_course_id
            and normalize_course_code(course.code) == normalized_code
        ),
        None,
    )


def reject_duplicate_code(
    code: str,
    database_session: Session,
    excluded_course_id: int | None = None,
) -> None:
    """Return 409 when another Course already uses the requested code."""
    if find_course_with_code(code, database_session, excluded_course_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A Course with code '{code}' already exists.",
        )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_course(
    course_data: CourseCreate,
    database_session: Session = Depends(get_db),
) -> Course:
    """Create a course when its code is not already in use."""
    reject_duplicate_code(course_data.code, database_session)

    course = Course(**course_data.model_dump())
    database_session.add(course)
    database_session.commit()
    database_session.refresh(course)
    return course


@router.get("", response_model=list[CourseResponse])
def get_courses(
    database_session: Session = Depends(get_db),
) -> list[Course]:
    """Return every course ordered by its database ID."""
    courses = database_session.scalars(select(Course).order_by(Course.id)).all()
    return list(courses)


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    database_session: Session = Depends(get_db),
) -> Course:
    """Return one course by ID."""
    return get_course_or_404(course_id, database_session)


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    course_data: CourseUpdate,
    database_session: Session = Depends(get_db),
) -> Course:
    """Replace an existing course with validated data."""
    course = get_course_or_404(course_id, database_session)
    reject_duplicate_code(
        course_data.code,
        database_session,
        excluded_course_id=course.id,
    )

    course.name = course_data.name
    course.code = course_data.code
    database_session.commit()
    database_session.refresh(course)
    return course


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_course(
    course_id: int,
    database_session: Session = Depends(get_db),
) -> Response:
    """Delete an empty Course while protecting linked academic work."""
    course = get_course_or_404(course_id, database_session)
    linked_assignment_id = database_session.scalar(
        select(Assignment.id)
        .where(Assignment.course_id == course.id)
        .limit(1)
    )
    if linked_assignment_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Course with id {course_id} cannot be deleted while it has "
                "Assignments. Remove or reassign them first."
            ),
        )

    linked_exam_id = database_session.scalar(
        select(Exam.id).where(Exam.course_id == course.id).limit(1)
    )
    if linked_exam_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Course with id {course_id} cannot be deleted while it has "
                "Exams. Remove or reassign them first."
            ),
        )

    database_session.delete(course)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
