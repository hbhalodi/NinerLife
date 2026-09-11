"""API route modules for NinerLife."""

from .assignments import router as assignments_router
from .courses import router as courses_router

__all__ = ["assignments_router", "courses_router"]
