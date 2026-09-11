"""Pydantic request and response schemas for the NinerLife API."""

from .assignment import AssignmentCreate, AssignmentResponse, AssignmentUpdate
from .course import CourseCreate, CourseResponse, CourseUpdate
from .dashboard import DashboardSummary, UpcomingExam
from .exam import ExamCreate, ExamResponse, ExamUpdate
from .insights import AssignmentInsight, AssignmentInsightCourse
from .study_plan import StudyPlanRecommendation, StudyPlanSummary

__all__ = [
    "AssignmentCreate",
    "AssignmentInsight",
    "AssignmentInsightCourse",
    "AssignmentResponse",
    "AssignmentUpdate",
    "CourseCreate",
    "CourseResponse",
    "CourseUpdate",
    "DashboardSummary",
    "ExamCreate",
    "ExamResponse",
    "ExamUpdate",
    "StudyPlanRecommendation",
    "StudyPlanSummary",
    "UpcomingExam",
]
