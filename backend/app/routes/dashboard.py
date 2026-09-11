"""Read-only API route for the NinerLife dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import DashboardSummary
from ..services import build_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    work_hours: Annotated[float, Query(ge=0)] = 0,
    database_session: Session = Depends(get_db),
) -> DashboardSummary:
    """Return workload counts and upcoming work without changing the database."""
    return build_dashboard_summary(database_session, work_hours=work_hours)
