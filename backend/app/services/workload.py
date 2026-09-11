"""Read-only workload calculations for the NinerLife dashboard."""

from datetime import date, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..models import Assignment, Course, Exam
from ..schemas.dashboard import (
    DashboardSummary,
    UpcomingExam,
)
from .prioritization import build_assignment_insight

WorkloadLevel = Literal["Low", "Medium", "High"]


def calculate_workload_score(
    course_count: int,
    weekly_assignment_count: int,
    weekly_exam_count: int,
    work_hours: float,
) -> float:
    """Apply the original NinerLife v1 workload weights exactly."""
    return (
        (course_count * 5)
        + (weekly_assignment_count * 5)
        + (weekly_exam_count * 10)
        + work_hours
    )


def get_workload_level(score: float) -> WorkloadLevel:
    """Return the original v1 workload level for a score."""
    if score < 40:
        return "Low"
    if score < 70:
        return "Medium"
    return "High"


def build_dashboard_summary(
    database_session: Session,
    work_hours: float = 0,
    reference_date: date | None = None,
) -> DashboardSummary:
    """Build a read-only dashboard summary for an inclusive seven-day window."""
    window_start = reference_date or date.today()
    window_end = window_start + timedelta(days=7)

    total_course_count = int(
        database_session.scalar(select(func.count(Course.id))) or 0
    )
    upcoming_assignments = list(
        database_session.scalars(
            select(Assignment)
            .options(joinedload(Assignment.course))
            .where(
                Assignment.completed.is_(False),
                Assignment.due >= window_start,
                Assignment.due <= window_end,
            )
            .order_by(Assignment.due, Assignment.id)
        ).all()
    )
    upcoming_exams = list(
        database_session.scalars(
            select(Exam)
            .options(joinedload(Exam.course))
            .where(
                Exam.completed.is_(False),
                Exam.exam_date >= window_start,
                Exam.exam_date <= window_end,
            )
            .order_by(Exam.exam_date, Exam.id)
        ).all()
    )
    overdue_incomplete_assignment_count = int(
        database_session.scalar(
            select(func.count(Assignment.id)).where(
                Assignment.completed.is_(False),
                Assignment.due < window_start,
            )
        )
        or 0
    )

    workload_score = calculate_workload_score(
        course_count=total_course_count,
        weekly_assignment_count=len(upcoming_assignments),
        weekly_exam_count=len(upcoming_exams),
        work_hours=work_hours,
    )

    return DashboardSummary(
        total_course_count=total_course_count,
        weekly_assignment_count=len(upcoming_assignments),
        weekly_exam_count=len(upcoming_exams),
        overdue_incomplete_assignment_count=overdue_incomplete_assignment_count,
        workload_score=workload_score,
        workload_level=get_workload_level(workload_score),
        work_hours=work_hours,
        window_start=window_start,
        window_end=window_end,
        upcoming_assignments=[
            build_assignment_insight(assignment, window_start)
            for assignment in upcoming_assignments
        ],
        upcoming_exams=[
            UpcomingExam.model_validate(exam) for exam in upcoming_exams
        ],
    )
