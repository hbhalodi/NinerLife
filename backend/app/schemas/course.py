"""Validation and serialization schemas for courses."""

from pydantic import BaseModel, ConfigDict, field_validator


class CourseFields(BaseModel):
    """Fields accepted when creating or replacing a course."""

    model_config = ConfigDict(extra="forbid")

    name: str
    code: str

    @field_validator("name", "code")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        """Trim required course text and reject blank values."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("must not be blank")
        return cleaned_value


class CourseCreate(CourseFields):
    """Data required to create a course."""


class CourseUpdate(CourseFields):
    """Complete replacement data for an existing course."""


class CourseResponse(CourseFields):
    """Course data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
