"""Read-only schemas for deterministic study-plan recommendations."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StudyPlanCourse(BaseModel):
    """Course identity included with a study-plan recommendation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class StudyPlanRecommendation(BaseModel):
    """One explainable, ordered study recommendation."""

    type: Literal["Assignment", "Exam"]
    id: int
    name: str
    course_id: int
    course: StudyPlanCourse
    date: date
    difficulty: Literal["Low", "Medium", "High"]
    estimated_hours: float = Field(ge=0)
    score: int = Field(ge=0)
    reasons: list[str]
    recommended_study_hours: float = Field(ge=0)


class StudyPlanSummary(BaseModel):
    """The read-only, time-bounded plan returned to the student."""

    available_hours: float = Field(gt=0)
    allocated_hours: float = Field(ge=0)
    remaining_hours: float = Field(ge=0)
    horizon_days: int = Field(ge=1, le=30)
    recommendations: list[StudyPlanRecommendation]
