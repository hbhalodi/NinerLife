"""Read-only deadline and priority calculations preserved from NinerLife v1."""

from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Assignment
from ..schemas.insights import AssignmentInsight

DeadlineStatus = Literal["Overdue", "Due Today", "Due Soon", "Upcoming"]
Difficulty = Literal["Low", "Medium", "High"]
Priority = Literal["Critical", "High", "Medium", "Low"]


def days_until_due(due_date: date, reference_date: date | None = None) -> int:
    """Return signed calendar days from the reference date to an assignment due date."""
    return (due_date - (reference_date or date.today())).days


def get_deadline_status(days_remaining: int) -> DeadlineStatus:
    """Apply the original NinerLife v1 deadline-status boundaries."""
    if days_remaining < 0:
        return "Overdue"
    if days_remaining == 0:
        return "Due Today"
    if days_remaining <= 2:
        return "Due Soon"
    return "Upcoming"


def normalize_difficulty(difficulty: object) -> Difficulty:
    """Normalize supported difficulty text to a consistent display value."""
    if not isinstance(difficulty, str):
        raise ValueError("Difficulty must be Low, Medium, or High.")

    normalized_difficulty = difficulty.strip().casefold()
    difficulty_values: dict[str, Difficulty] = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    }
    if normalized_difficulty not in difficulty_values:
        raise ValueError("Difficulty must be Low, Medium, or High.")
    return difficulty_values[normalized_difficulty]


def calculate_priority(days_remaining: int, difficulty: object) -> Priority:
    """Apply the original NinerLife v1 priority rules without changing data."""
    normalized_difficulty = normalize_difficulty(difficulty)

    if normalized_difficulty == "High":
        if days_remaining <= 2:
            return "Critical"
        if days_remaining <= 5:
            return "High"
        return "Medium"

    if normalized_difficulty == "Medium":
        if days_remaining <= 2:
            return "High"
        if days_remaining <= 5:
            return "Medium"
        return "Low"

    if days_remaining <= 2:
        return "Medium"
    return "Low"


def build_assignment_insight(
    assignment: Assignment,
    reference_date: date | None = None,
) -> AssignmentInsight:
    """Return read-only deadline and priority data for one assignment."""
    normalized_difficulty = normalize_difficulty(assignment.difficulty)
    remaining_days = days_until_due(assignment.due, reference_date)

    return AssignmentInsight(
        id=assignment.id,
        name=assignment.name,
        course_id=assignment.course_id,
        course=assignment.course,
        due=assignment.due,
        difficulty=normalized_difficulty,
        estimated_hours=assignment.estimated_hours,
        completed=assignment.completed,
        days_until_due=remaining_days,
        deadline_status=get_deadline_status(remaining_days),
        priority=calculate_priority(remaining_days, normalized_difficulty),
    )


def get_assignment_insights(
    database_session: Session,
    reference_date: date | None = None,
) -> list[AssignmentInsight]:
    """Read every assignment with its Course and calculated insight fields."""
    assignments = database_session.scalars(
        select(Assignment)
        .options(joinedload(Assignment.course))
        .order_by(Assignment.due, Assignment.id)
    ).all()
    return [
        build_assignment_insight(assignment, reference_date)
        for assignment in assignments
    ]
