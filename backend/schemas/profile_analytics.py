from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ProfileResponse(BaseModel):
    """
    Used by GET /profile/me. Kept in sync with stats_service so that IF
    this endpoint is ever wired into the frontend, it can't disagree with
    /students/profile-info or /analytics/summary.
    """
    name: str
    email: str
    created_at: datetime
    total_quizzes: int
    accuracy: float


class RecentActivityItem(BaseModel):
    type: str          # "quiz" | "note"
    label: str         # e.g. "Quiz on Photosynthesis" / "Notes on Photosynthesis"
    topic: Optional[str] = None
    accuracy: Optional[float] = None  # only present for quiz activity
    timestamp: datetime


class TopicBreakdownItem(BaseModel):
    topic: str
    attempts: int
    average_accuracy: float


class WeeklyActivityItem(BaseModel):
    week_start: str   # ISO date, Monday of that week
    count: int


class MonthlyActivityItem(BaseModel):
    month: str         # "YYYY-MM"
    count: int


class LearningTrendPoint(BaseModel):
    period: str         # ISO date, Monday of that week
    average_accuracy: float


class AnalyticsSummaryResponse(BaseModel):
    # Existing fields (unchanged shape — frontend already depends on these)
    total_quizzes: int
    average_accuracy: float
    total_notes_generated: int
    total_quizzes_generated: int
    recent_activity: List[RecentActivityItem]

    # New fields (this audit)
    quiz_questions_answered: int       # sum of total_questions across all attempts
    documents_uploaded: int
    estimated_study_minutes: int       # see stats_service.get_estimated_study_minutes
    topic_breakdown: List[TopicBreakdownItem]
    weekly_activity: List[WeeklyActivityItem]
    monthly_activity: List[MonthlyActivityItem]
    learning_trend: List[LearningTrendPoint]


class ProfileInfoResponse(BaseModel):
    """
    Used by GET /students/profile-info — the richer, profile-page-specific
    endpoint. Replaces the previous untyped dict return.
    """
    student_id: int
    name: str
    email: str
    joined: datetime              # User.created_at — account creation date
    topic: Optional[str] = None
    level: str
    accuracy: float
    total_quizzes: int
    correct_answers: int
    notes_topics: List[str]       # kept for backward compatibility
    topics_studied: List[str]     # merged Notes + QuizResult topics (superset)

    # New fields (this audit)
    total_questions_asked: int
    total_study_sessions: int
    total_documents_uploaded: int
    current_streak: int