"""Response schemas for the NinerLife dashboard."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .insights import AssignmentInsight, AssignmentInsightCourse


class UpcomingExam(BaseModel):
    """An incomplete exam in the dashboard's weekly window."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    exam_date: date
    difficulty: str
    course: AssignmentInsightCourse


class DashboardSummary(BaseModel):
    """Read-only workload and upcoming-work data for the dashboard."""

    total_course_count: int = Field(ge=0)
    weekly_assignment_count: int = Field(ge=0)
    weekly_exam_count: int = Field(ge=0)
    overdue_incomplete_assignment_count: int = Field(ge=0)
    workload_score: float = Field(ge=0)
    workload_level: Literal["Low", "Medium", "High"]
    work_hours: float = Field(ge=0)
    window_start: date
    window_end: date
    upcoming_assignments: list[AssignmentInsight]
    upcoming_exams: list[UpcomingExam]
