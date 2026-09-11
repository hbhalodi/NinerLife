"""Validation and serialization schemas for exams."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExamFields(BaseModel):
    """Fields accepted when creating or replacing an exam."""

    model_config = ConfigDict(extra="forbid")

    name: str
    course_id: int = Field(gt=0)
    exam_date: date
    difficulty: str
    estimated_study_hours: float = Field(ge=0)
    completed: bool = Field(default=False, strict=True)

    @field_validator("name", "difficulty")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        """Trim required Exam text and reject blank values."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("must not be blank")
        return cleaned_value


class ExamCreate(ExamFields):
    """Data required to create an exam."""


class ExamUpdate(ExamFields):
    """Complete replacement data for an existing exam."""


class ExamResponse(ExamFields):
    """Exam data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
