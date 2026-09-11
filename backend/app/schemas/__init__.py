"""Pydantic request and response schemas for the NinerLife API."""

from .assignment import AssignmentCreate, AssignmentResponse, AssignmentUpdate
from .course import CourseCreate, CourseResponse, CourseUpdate

__all__ = [
    "AssignmentCreate",
    "AssignmentResponse",
    "AssignmentUpdate",
    "CourseCreate",
    "CourseResponse",
    "CourseUpdate",
]
