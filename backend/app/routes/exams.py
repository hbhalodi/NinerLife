"""REST API routes for exam management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Course, Exam
from ..schemas import ExamCreate, ExamResponse, ExamUpdate

router = APIRouter(prefix="/exams", tags=["exams"])


def get_exam_or_404(exam_id: int, database_session: Session) -> Exam:
    """Return an exam or raise a clear not-found response."""
    exam = database_session.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with id {exam_id} was not found.",
        )
    return exam


def verify_course_exists(course_id: int, database_session: Session) -> None:
    """Reject an Exam request that references an unknown Course."""
    if database_session.get(Course, course_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} was not found.",
        )


@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exam(
    exam_data: ExamCreate,
    database_session: Session = Depends(get_db),
) -> Exam:
    """Create an Exam linked to an existing Course."""
    verify_course_exists(exam_data.course_id, database_session)

    exam = Exam(**exam_data.model_dump())
    database_session.add(exam)
    database_session.commit()
    database_session.refresh(exam)
    return exam


@router.get("", response_model=list[ExamResponse])
def get_exams(
    database_session: Session = Depends(get_db),
) -> list[Exam]:
    """Return every Exam ordered by its database ID."""
    exams = database_session.scalars(select(Exam).order_by(Exam.id)).all()
    return list(exams)


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    database_session: Session = Depends(get_db),
) -> Exam:
    """Return one Exam by ID."""
    return get_exam_or_404(exam_id, database_session)


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    exam_data: ExamUpdate,
    database_session: Session = Depends(get_db),
) -> Exam:
    """Replace an existing Exam with validated data."""
    exam = get_exam_or_404(exam_id, database_session)
    verify_course_exists(exam_data.course_id, database_session)

    for field_name, value in exam_data.model_dump().items():
        setattr(exam, field_name, value)

    database_session.commit()
    database_session.refresh(exam)
    return exam


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_exam(
    exam_id: int,
    database_session: Session = Depends(get_db),
) -> Response:
    """Delete an Exam by ID."""
    exam = get_exam_or_404(exam_id, database_session)
    database_session.delete(exam)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
