"""Read-only schemas for assignment deadline and priority insights."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DeadlineStatus = Literal["Overdue", "Due Today", "Due Soon", "Upcoming"]
Priority = Literal["Critical", "High", "Medium", "Low"]


class AssignmentInsightCourse(BaseModel):
    """Course identity included with an assignment insight."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class AssignmentInsight(BaseModel):
    """An assignment plus its read-only deadline and priority information."""

    id: int
    name: str
    course_id: int
    course: AssignmentInsightCourse
    due: date
    difficulty: Literal["Low", "Medium", "High"]
    estimated_hours: float = Field(ge=0)
    completed: bool
    days_until_due: int
    deadline_status: DeadlineStatus
    priority: Priority
