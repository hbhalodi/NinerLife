"""SQLAlchemy models for the NinerLife database."""

from .assignment import Assignment
from .course import Course
from .exam import Exam

__all__ = ["Assignment", "Course", "Exam"]
