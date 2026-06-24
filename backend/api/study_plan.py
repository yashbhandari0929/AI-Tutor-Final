from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database.database import SessionLocal
from database.models import StudentProfile, User
from schemas.study_plan import DailyTaskOut, StudyPlanResponse, TopicMasteryOut, WeeklyGoalOut
from services.study_plan_service import TopicMastery, build_study_plan

router = APIRouter(tags=["Study Plan"])


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


@router.get("/study-plan", response_model=StudyPlanResponse)
def study_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student:
        return StudyPlanResponse(
            overall_accuracy=0.0,
            accuracy_tier="foundation",
            difficulty_level="easy",
            weak_topics=[],
            strong_topics=[],
            mastery_scores=[],
            daily_plan=[],
            weekly_plan=[],
            recommendations=["Take your first quiz to generate a personalized study plan."],
            estimated_hours_to_next_tier=0.0,
            estimated_completion_date=None,
            current_streak=0,
            documents_available=0,
            plan_generated_at="",
        )

    plan = build_study_plan(db, student)
    return StudyPlanResponse(
        overall_accuracy=plan.overall_accuracy,
        accuracy_tier=plan.accuracy_tier,
        difficulty_level=plan.difficulty_level,
        weak_topics=[_mastery_to_out(m) for m in plan.weak_topics],
        strong_topics=[_mastery_to_out(m) for m in plan.strong_topics],
        mastery_scores=[_mastery_to_out(m) for m in plan.all_mastery_scores],
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
        recommendations=plan.recommendations,
        estimated_hours_to_next_tier=plan.estimated_hours_to_next_tier,
        estimated_completion_date=plan.estimated_completion_date,
        current_streak=plan.current_streak,
        documents_available=plan.documents_available,
        plan_generated_at=plan.plan_generated_at,
    )
