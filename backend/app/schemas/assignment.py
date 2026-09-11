"""Validation and serialization schemas for assignments."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssignmentFields(BaseModel):
    """Fields accepted when creating or replacing an assignment."""

    model_config = ConfigDict(extra="forbid")

    name: str
    course_id: int = Field(gt=0)
    due: date
    difficulty: str
    estimated_hours: float = Field(ge=0)
    completed: bool = Field(default=False, strict=True)

    @field_validator("name", "difficulty")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        """Reject empty or whitespace-only required text fields."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("must not be blank")
        return cleaned_value


class AssignmentCreate(AssignmentFields):
    """Data required to create an assignment."""


class AssignmentUpdate(AssignmentFields):
    """Complete replacement data for an existing assignment."""


class AssignmentResponse(AssignmentFields):
    """Assignment data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
