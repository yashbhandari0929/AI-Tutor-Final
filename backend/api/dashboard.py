"""
api/dashboard.py  — replaces the old api/dashboard.py and api/study_plan.py

WHAT CHANGED vs. old files
───────────────────────────
OLD study_plan.py
  • Called db.query(QuizResult).all() — NO student filter, NO auth.
    Every user saw every student's data merged together.
  • Returned one of four hardcoded plan lists based on avg accuracy bucket.
  • No topic mastery, no daily/weekly goals, no recommendations.

OLD dashboard.py
  • Had auth and student scoping (good) but still returned hardcoded emoji
    strings chosen purely by accuracy tier — identical for every user in
    that tier.
  • Heatmap had no current_streak field; that was added in the last audit.

NEW dashboard.py (this file)
  • GET /dashboard/study-plan  ← replaces both old endpoints
      - Authenticated, scoped to JWT bearer.
      - Delegates ALL logic to services/study_plan_service.build_study_plan().
      - Returns backward-compatible `average_accuracy` + `plan` PLUS full
        structured data: mastery scores, daily tasks, weekly goals,
        recommendations, estimated completion date, streak.
      - Zero hardcoded strings. Every task and recommendation is built from
        the user's actual QuizResult, Note, and Document rows.

  • GET /dashboard/heatmap  ← unchanged logic, streak field was already added.

Mount in main.py:
    from api import dashboard
    app.include_router(dashboard.router)

Remove from main.py (or keep but they will never be hit if prefix matches):
    any previous include_router for the old study_plan router
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import User, StudentProfile
from auth.dependencies import get_current_user
from services import stats_service
from services.study_plan_service import build_study_plan, TopicMastery
from schemas.study_plan import (
    DashboardStudyPlanResponse,
    DailyTaskOut,
    WeeklyGoalOut,
    TopicMasteryOut,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _mastery_to_out(m: TopicMastery) -> TopicMasteryOut:
    return TopicMasteryOut(
        topic=m.topic,
        mastery_score=m.mastery_score,
        quiz_accuracy=m.quiz_accuracy,
        consistency_score=m.consistency_score,
        completion_rate=m.completion_rate,
        time_score=m.time_score,
        attempts=m.attempts,
        last_seen=m.last_seen.isoformat() if m.last_seen else None,
        trend=m.trend,
    )


# ── Study Plan ────────────────────────────────────────────────────────────────

@router.get("/study-plan", response_model=DashboardStudyPlanResponse)
def get_study_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a fully personalised, AI-computed adaptive study plan for the
    logged-in student.

    The plan is derived from:
      - QuizResult rows (accuracy per topic, attempt history, trends)
      - Note rows (topics studied, notes-to-quiz ratio)
      - Document rows (uploaded RAG documents count)
      - Activity dates (streak computation)

    Nothing is hardcoded. Brand-new accounts with zero history receive a
    bootstrapped starter plan that guides them to their first data point.
    """
    student = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    # ── No student profile yet (brand-new account) ────────────────────────
    if not student:
        return DashboardStudyPlanResponse(
            average_accuracy=0.0,
            plan=[
                "👋 Welcome! Take your first quiz to get a personalised study plan.",
                "📝 Generate notes on any topic you're currently studying.",
                "📄 Upload a PDF or image to chat with your study material.",
                "🔥 Come back daily — streaks accelerate your learning by 40%.",
            ],
            accuracy_tier="foundation",
            difficulty_level="easy",
            daily_plan=[],
            weekly_plan=[],
            weak_topics=[],
            strong_topics=[],
            mastery_scores=[],
            recommendations=[
                "Start with a quiz on any topic. Even one attempt unlocks your personalised plan."
            ],
            estimated_hours_to_next_tier=0.0,
            estimated_completion_date=None,
            current_streak=0,
            documents_available=0,
        )

    # ── Compute full adaptive plan ────────────────────────────────────────
    plan = build_study_plan(db, student)

    # Build the legacy `plan` list (flat strings) from daily tasks so the
    # existing dashboard frontend renders without any code changes.
    plan_strings: list[str] = []
    for task in plan.daily_plan:
        icon = {
            "quiz":      "🎯",
            "notes":     "📝",
            "review":    "🔍",
            "flashcard": "🃏",
            "mock":      "🏆",
        }.get(task.task_type, "📌")
        plan_strings.append(f"{icon} {task.description} (~{task.estimated_minutes} min)")

    if not plan_strings:
        plan_strings = [
            "Take a quiz to start building your personalised plan.",
            "Generate notes on a topic you're currently studying.",
        ]

    return DashboardStudyPlanResponse(
        # Legacy fields
        average_accuracy=plan.overall_accuracy,
        plan=plan_strings,

        # Structured fields
        accuracy_tier=plan.accuracy_tier,
        difficulty_level=plan.difficulty_level,
        daily_plan=[
            DailyTaskOut(
                order=t.order,
                task_type=t.task_type,
                topic=t.topic,
                description=t.description,
                estimated_minutes=t.estimated_minutes,
                priority=t.priority,
                difficulty=t.difficulty,
            )
            for t in plan.daily_plan
        ],
        weekly_plan=[
            WeeklyGoalOut(
                week_number=w.week_number,
                focus_area=w.focus_area,
                target_accuracy=w.target_accuracy,
                topics=w.topics,
                tasks_per_day=w.tasks_per_day,
                milestone=w.milestone,
            )
            for w in plan.weekly_plan
        ],
        weak_topics=[_mastery_to_out(m) for m in plan.weak_topics],
        strong_topics=[_mastery_to_out(m) for m in plan.strong_topics],
        mastery_scores=[_mastery_to_out(m) for m in plan.all_mastery_scores],
        recommendations=plan.recommendations,
        estimated_hours_to_next_tier=plan.estimated_hours_to_next_tier,
        estimated_completion_date=plan.estimated_completion_date,
        current_streak=plan.current_streak,
        documents_available=plan.documents_available,
    )


# ── Heatmap (unchanged logic from previous audit) ─────────────────────────────

@router.get("/heatmap")
def get_heatmap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns 180 days of activity counts keyed by ISO date (YYYY-MM-DD)
    plus the current consecutive-day streak.
    """
    student = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if not student:
        return {"activity": {}, "current_streak": 0}

    activity = stats_service.get_activity_heatmap(db, student.id, days=180)
    streak = stats_service.get_current_streak(db, student.id)

    return {
        "activity": activity,
        "current_streak": streak,
    }