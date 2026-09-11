"""API route modules for NinerLife."""

from .assignments import router as assignments_router
from .courses import router as courses_router
from .exams import router as exams_router

__all__ = ["assignments_router", "courses_router", "exams_router"]
