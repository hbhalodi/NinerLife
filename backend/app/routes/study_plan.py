"""Read-only API route for deterministic study-plan recommendations."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import StudyPlanSummary
from ..services import build_study_plan

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


@router.get("", response_model=StudyPlanSummary)
def get_study_plan(
    available_hours: Annotated[float, Query(gt=0)] = 4,
    horizon_days: Annotated[int, Query(ge=1, le=30)] = 7,
    database_session: Session = Depends(get_db),
) -> StudyPlanSummary:
    """Return an explainable plan without writing to the database."""
    try:
        return build_study_plan(
            database_session,
            available_hours=available_hours,
            horizon_days=horizon_days,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
