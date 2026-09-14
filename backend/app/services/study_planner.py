"""Deterministic, explainable study planning built from existing academic data."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Assignment, Course, Exam
from ..schemas.study_plan import StudyPlanRecommendation, StudyPlanSummary
from .prioritization import days_until_due, normalize_difficulty
from .assignment_history import purge_expired_assignment_history

OVERDUE_URGENCY_SCORE = 60
NEAR_URGENCY_SCORE = 50
SOON_URGENCY_SCORE = 35
WEEK_URGENCY_SCORE = 20
LATER_URGENCY_SCORE = 10

DIFFICULTY_SCORES = {
    "High": 20,
    "Medium": 10,
    "Low": 5,
}
EXAM_TYPE_BONUS = 10

ItemType = Literal["Assignment", "Exam"]


@dataclass(frozen=True)
class PlannerCandidate:
    """Internal representation used for deterministic ranking and allocation."""

    item_type: ItemType
    id: int
    name: str
    course_id: int
    course: Course
    item_date: date
    difficulty: Literal["Low", "Medium", "High"]
    estimated_hours: float
    score: int
    reasons: list[str]


def get_urgency_score(days_remaining: int) -> int:
    """Return the centralized urgency contribution for signed calendar days."""
    if days_remaining < 0:
        return OVERDUE_URGENCY_SCORE
    if days_remaining <= 2:
        return NEAR_URGENCY_SCORE
    if days_remaining <= 5:
        return SOON_URGENCY_SCORE
    if days_remaining <= 7:
        return WEEK_URGENCY_SCORE
    return LATER_URGENCY_SCORE


def get_difficulty_score(difficulty: object) -> int:
    """Return the centralized difficulty contribution using canonical text."""
    return DIFFICULTY_SCORES[normalize_difficulty(difficulty)]


def get_type_score(item_type: ItemType) -> int:
    """Exams receive the fixed type bonus; assignments receive no type bonus."""
    return EXAM_TYPE_BONUS if item_type == "Exam" else 0


def calculate_planner_score(
    days_remaining: int,
    difficulty: object,
    item_type: ItemType,
) -> int:
    """Combine explainable urgency, difficulty, and type contributions."""
    return (
        get_urgency_score(days_remaining)
        + get_difficulty_score(difficulty)
        + get_type_score(item_type)
    )


def get_urgency_reason(days_remaining: int, item_type: ItemType) -> str:
    """Describe the urgency contribution included in a recommendation score."""
    urgency_score = get_urgency_score(days_remaining)
    if days_remaining < 0:
        return f"Overdue assignment (+{urgency_score})"
    if days_remaining == 0:
        label = "Due today" if item_type == "Assignment" else "Exam today"
        return f"{label} (+{urgency_score})"

    date_label = "Due" if item_type == "Assignment" else "Exam"
    day_label = "day" if days_remaining == 1 else "days"
    return f"{date_label} in {days_remaining} {day_label} (+{urgency_score})"


def build_assignment_candidate(
    assignment: Assignment,
    reference_date: date,
) -> PlannerCandidate:
    """Turn a filtered assignment into an explainable planning candidate."""
    difficulty = normalize_difficulty(assignment.difficulty)
    remaining_days = days_until_due(assignment.due, reference_date)
    difficulty_score = get_difficulty_score(difficulty)

    return PlannerCandidate(
        item_type="Assignment",
        id=assignment.id,
        name=assignment.name,
        course_id=assignment.course_id,
        course=assignment.course,
        item_date=assignment.due,
        difficulty=difficulty,
        estimated_hours=assignment.estimated_hours,
        score=calculate_planner_score(remaining_days, difficulty, "Assignment"),
        reasons=[
            get_urgency_reason(remaining_days, "Assignment"),
            f"{difficulty} difficulty (+{difficulty_score})",
        ],
    )


def build_exam_candidate(exam: Exam, reference_date: date) -> PlannerCandidate:
    """Turn a filtered exam into an explainable planning candidate."""
    difficulty = normalize_difficulty(exam.difficulty)
    remaining_days = days_until_due(exam.exam_date, reference_date)
    difficulty_score = get_difficulty_score(difficulty)

    return PlannerCandidate(
        item_type="Exam",
        id=exam.id,
        name=exam.name,
        course_id=exam.course_id,
        course=exam.course,
        item_date=exam.exam_date,
        difficulty=difficulty,
        estimated_hours=exam.estimated_study_hours,
        score=calculate_planner_score(remaining_days, difficulty, "Exam"),
        reasons=[
            get_urgency_reason(remaining_days, "Exam"),
            f"{difficulty} difficulty (+{difficulty_score})",
            f"Exam (+{EXAM_TYPE_BONUS})",
        ],
    )


def build_study_plan(
    database_session: Session,
    available_hours: float = 4,
    horizon_days: int = 7,
    reference_date: date | None = None,
) -> StudyPlanSummary:
    """Create a read-only plan by ranking candidates and allocating time in order."""
    if available_hours <= 0:
        raise ValueError("available_hours must be greater than zero.")
    if not 1 <= horizon_days <= 30:
        raise ValueError("horizon_days must be between 1 and 30.")

    purge_expired_assignment_history(database_session)
    today = reference_date or date.today()
    horizon_end = today + timedelta(days=horizon_days)
    assignments = database_session.scalars(
        select(Assignment)
        .options(joinedload(Assignment.course))
        .where(
            Assignment.completed.is_(False),
            Assignment.due <= horizon_end,
        )
    ).all()
    exams = database_session.scalars(
        select(Exam)
        .options(joinedload(Exam.course))
        .where(
            Exam.completed.is_(False),
            Exam.exam_date >= today,
            Exam.exam_date <= horizon_end,
        )
    ).all()

    candidates = [
        *(build_assignment_candidate(assignment, today) for assignment in assignments),
        *(build_exam_candidate(exam, today) for exam in exams),
    ]
    candidates.sort(
        key=lambda candidate: (
            -candidate.score,
            candidate.item_date,
            candidate.id,
            candidate.name.casefold(),
            candidate.item_type,
        )
    )

    remaining_hours = float(available_hours)
    recommendations: list[StudyPlanRecommendation] = []
    for candidate in candidates:
        recommended_hours = min(candidate.estimated_hours, remaining_hours)
        recommended_hours = max(0.0, recommended_hours)
        remaining_hours = max(0.0, remaining_hours - recommended_hours)
        recommendations.append(
            StudyPlanRecommendation(
                type=candidate.item_type,
                id=candidate.id,
                name=candidate.name,
                course_id=candidate.course_id,
                course=candidate.course,
                date=candidate.item_date,
                difficulty=candidate.difficulty,
                estimated_hours=candidate.estimated_hours,
                score=candidate.score,
                reasons=candidate.reasons,
                recommended_study_hours=recommended_hours,
            )
        )

    remaining_hours = round(remaining_hours, 10)
    allocated_hours = round(float(available_hours) - remaining_hours, 10)
    return StudyPlanSummary(
        available_hours=available_hours,
        allocated_hours=allocated_hours,
        remaining_hours=remaining_hours,
        horizon_days=horizon_days,
        recommendations=recommendations,
    )
