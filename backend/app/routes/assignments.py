"""REST API routes for assignment management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Assignment, Course
from ..schemas import AssignmentCreate, AssignmentResponse, AssignmentUpdate

router = APIRouter(prefix="/assignments", tags=["assignments"])


def get_assignment_or_404(assignment_id: int, database_session: Session) -> Assignment:
    """Return an assignment or raise a clear not-found response."""
    assignment = database_session.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with id {assignment_id} was not found.",
        )
    return assignment


def verify_course_exists(course_id: int, database_session: Session) -> None:
    """Reject an assignment request that references an unknown course."""
    if database_session.get(Course, course_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} was not found.",
        )


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    assignment_data: AssignmentCreate,
    database_session: Session = Depends(get_db),
) -> Assignment:
    """Create an assignment linked to an existing course."""
    verify_course_exists(assignment_data.course_id, database_session)

    assignment = Assignment(**assignment_data.model_dump())
    database_session.add(assignment)
    database_session.commit()
    database_session.refresh(assignment)
    return assignment


@router.get("", response_model=list[AssignmentResponse])
def get_assignments(
    database_session: Session = Depends(get_db),
) -> list[Assignment]:
    """Return every assignment ordered by its database ID."""
    assignments = database_session.scalars(
        select(Assignment).order_by(Assignment.id)
    ).all()
    return list(assignments)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: int,
    database_session: Session = Depends(get_db),
) -> Assignment:
    """Return one assignment by ID."""
    return get_assignment_or_404(assignment_id, database_session)


@router.put("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    assignment_data: AssignmentUpdate,
    database_session: Session = Depends(get_db),
) -> Assignment:
    """Replace an existing assignment with validated data."""
    assignment = get_assignment_or_404(assignment_id, database_session)
    verify_course_exists(assignment_data.course_id, database_session)

    for field_name, value in assignment_data.model_dump().items():
        setattr(assignment, field_name, value)

    database_session.commit()
    database_session.refresh(assignment)
    return assignment


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment(
    assignment_id: int,
    database_session: Session = Depends(get_db),
) -> Response:
    """Delete an assignment by ID."""
    assignment = get_assignment_or_404(assignment_id, database_session)
    database_session.delete(assignment)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
