from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import User, StudentProfile, Note, QuizResult
from auth.dependencies import get_current_user
from services import stats_service
from schemas.profile_analytics import (
    AnalyticsSummaryResponse,
    RecentActivityItem,
    TopicBreakdownItem,
    WeeklyActivityItem,
    MonthlyActivityItem,
    LearningTrendPoint,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

RECENT_ACTIVITY_LIMIT = 10


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Every number below comes from services/stats_service.py — the same
    module api/student.py and api/dashboard.py use — so this endpoint
    cannot disagree with the Profile page or Dashboard about accuracy,
    quiz counts, or anything else. Scoped to the logged-in user via JWT;
    student_id is never taken from client input.

    If the user has no StudentProfile row, all stats are zero/empty
    rather than raising — a brand-new account's analytics page should
    look empty, not error out.
    """
    student = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )

    if not student:
        return AnalyticsSummaryResponse(
            total_quizzes=0,
            average_accuracy=0.0,
            total_notes_generated=0,
            total_quizzes_generated=0,
            recent_activity=[],
            quiz_questions_answered=0,
            documents_uploaded=0,
            estimated_study_minutes=0,
            topic_breakdown=[],
            weekly_activity=[],
            monthly_activity=[],
            learning_trend=[],
        )

    quiz_stats = stats_service.get_quiz_stats(db, student.id)
    notes_count = stats_service.get_notes_count(db, student.id)

    # ── Recent activity: merge quizzes + notes into one timeline ──────────────
    quizzes = (
        db.query(QuizResult)
        .filter(QuizResult.student_id == student.id)
        .order_by(QuizResult.created_at.desc())
        .all()
    )
    notes = (
        db.query(Note)
        .filter(Note.student_id == student.id)
        .order_by(Note.created_at.desc())
        .all()
    )

    activity: list[RecentActivityItem] = []
    for q in quizzes:
        activity.append(
            RecentActivityItem(
                type="quiz",
                label=f"Quiz on {q.topic}" if q.topic else "Quiz attempt",
                topic=q.topic,
                accuracy=q.accuracy,
                timestamp=q.created_at,
            )
        )
    for n in notes:
        activity.append(
            RecentActivityItem(
                type="note",
                label=f"Notes on {n.topic}" if n.topic else "Notes generated",
                topic=n.topic,
                accuracy=None,
                timestamp=n.created_at,
            )
        )
    activity.sort(key=lambda item: item.timestamp, reverse=True)
    recent_activity = activity[:RECENT_ACTIVITY_LIMIT]

    topic_breakdown = [
        TopicBreakdownItem(**t) for t in stats_service.get_topic_breakdown(db, student.id)
    ]
    weekly_activity = [
        WeeklyActivityItem(**w) for w in stats_service.get_weekly_activity(db, student.id)
    ]
    monthly_activity = [
        MonthlyActivityItem(**m) for m in stats_service.get_monthly_activity(db, student.id)
    ]
    learning_trend = [
        LearningTrendPoint(**p) for p in stats_service.get_learning_trend(db, student.id)
    ]

    return AnalyticsSummaryResponse(
        total_quizzes=quiz_stats.total_attempts,
        average_accuracy=quiz_stats.average_accuracy,
        total_notes_generated=notes_count,
        total_quizzes_generated=quiz_stats.total_attempts,
        recent_activity=recent_activity,
        quiz_questions_answered=quiz_stats.total_questions,
        documents_uploaded=stats_service.get_documents_count(db, student.id),
        estimated_study_minutes=stats_service.get_estimated_study_minutes(db, student.id),
        topic_breakdown=topic_breakdown,
        weekly_activity=weekly_activity,
        monthly_activity=monthly_activity,
        learning_trend=learning_trend,
    )