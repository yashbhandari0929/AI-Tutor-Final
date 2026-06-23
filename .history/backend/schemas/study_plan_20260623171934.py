"""
schemas/study_plan.py

Pydantic response models for the /study-plan and /dashboard endpoints.
All fields map 1-to-1 to AdaptiveStudyPlan dataclass fields from
services/study_plan_service.py — nothing is invented here.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class TopicMasteryOut(BaseModel):
    topic: str
    mastery_score: float
    quiz_accuracy: float
    consistency_score: float
    completion_rate: float
    time_score: float
    attempts: int
    last_seen: Optional[str]   # ISO date or null
    trend: str                 # "improving" | "declining" | "stable" | "new"


class DailyTaskOut(BaseModel):
    order: int
    task_type: str             # "quiz" | "notes" | "review" | "flashcard" | "mock"
    topic: str
    description: str
    estimated_minutes: int
    priority: str              # "high" | "medium" | "low"
    difficulty: str            # "easy" | "medium" | "hard" | "expert"


class WeeklyGoalOut(BaseModel):
    week_number: int
    focus_area: str
    target_accuracy: float
    topics: list[str]
    tasks_per_day: int
    milestone: str


class StudyPlanResponse(BaseModel):
    """
    Full response returned by GET /study-plan.
    Also used by GET /dashboard/study-plan (returns a subset of fields
    for backward compatibility with the existing dashboard frontend).
    """
    overall_accuracy: float
    accuracy_tier: str           # "foundation" | "building" | "advancing" | "mastery"
    difficulty_level: str        # recommended difficulty for next quiz

    weak_topics: list[TopicMasteryOut]
    strong_topics: list[TopicMasteryOut]
    mastery_scores: list[TopicMasteryOut]   # all topics, sorted by mastery asc

    daily_plan: list[DailyTaskOut]
    weekly_plan: list[WeeklyGoalOut]

    recommendations: list[str]
    estimated_hours_to_next_tier: float
    estimated_completion_date: Optional[str]
    current_streak: int
    documents_available: int
    plan_generated_at: str


class DashboardStudyPlanResponse(BaseModel):
    """
    Backward-compatible subset used by the existing dashboard frontend.
    Keeps the old `average_accuracy` + `plan` shape so the dashboard page
    requires zero changes for the basic study plan list.
    Also includes new structured fields that the updated frontend can
    optionally consume.
    """
    # Legacy fields (dashboard/page.tsx already reads these)
    average_accuracy: float
    plan: list[str]             # human-readable plan steps (one line each)

    # New structured fields (opt-in for updated frontend)
    accuracy_tier: str
    difficulty_level: str
    daily_plan: list[DailyTaskOut]
    weekly_plan: list[WeeklyGoalOut]
    weak_topics: list[TopicMasteryOut]
    strong_topics: list[TopicMasteryOut]
    mastery_scores: list[TopicMasteryOut]
    recommendations: list[str]
    estimated_hours_to_next_tier: float
    estimated_completion_date: Optional[str]
    current_streak: int
    documents_available: int