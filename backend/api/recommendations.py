from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database.database import SessionLocal
from database.models import Note, User, StudentProfile
from services.topic_mastery_service import get_student_mastery

router = APIRouter(tags=["Recommendations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _student(db: Session, user: User) -> StudentProfile | None:
    return db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()


def _trend(row) -> str:
    if row.attempts <= 10:
        return "new"
    if row.mastery_level in {"Strong", "Mastered"}:
        return "improving"
    return "stable"


def _topic(row, db: Session) -> dict:
    notes_used = (
        db.query(Note)
        .filter(Note.student_id == row.student_id, Note.topic == row.topic)
        .count()
    )
    return {
        "topic": row.topic,
        "mastery": row.mastery_score,
        "accuracy": row.accuracy,
        "attempts": row.attempts,
        "correct_answers": row.correct_answers,
        "notes_used": notes_used,
        "trend": _trend(row),
        "consistency": min(row.attempts / 40 * 100, 100),
        "score": row.mastery_score,
        "last_practiced": row.last_practiced.isoformat() if row.last_practiced else None,
    }


@router.get("/recommendations")
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student(db, current_user)
    if not student:
        return {
            "learning_score": 0,
            "weak_topics": [],
            "strong_topics": [],
            "recommendations": [],
        }

    rows = get_student_mastery(db, student.id)
    weak = [row for row in rows if row.mastery_level in {"Needs Work", "Weak", "Improving"}]
    strong = [row for row in rows if row.mastery_level in {"Strong", "Mastered"}]
    weak.sort(key=lambda row: (row.mastery_score, row.accuracy))
    strong.sort(key=lambda row: (-row.mastery_score, -row.accuracy))

    learning_score = round(sum(row.mastery_score for row in rows) / len(rows), 1) if rows else 0
    recommendations = []
    if weak:
        recommendations.append({
            "type": "mastery",
            "title": f"Practice {weak[0].topic}",
            "description": f"{weak[0].topic} is at {weak[0].mastery_score:.1f}% mastery. Start with notes, then take a focused quiz.",
            "priority": "high",
        })
    if len(weak) > 1:
        recommendations.append({
            "type": "review",
            "title": "Review your second weak topic",
            "description": f"Add a short review block for {weak[1].topic} to prevent the gap from widening.",
            "priority": "medium",
        })
    if strong:
        recommendations.append({
            "type": "retention",
            "title": f"Maintain {strong[0].topic}",
            "description": "Use one timed question set this week to keep your strongest topic fresh.",
            "priority": "low",
        })
    if not recommendations:
        recommendations.append({
            "type": "baseline",
            "title": "Create your first baseline",
            "description": "Take a quiz on any current topic to unlock personalized strengths, weak areas, and study tasks.",
            "priority": "high",
        })

    return {
        "learning_score": learning_score,
        "weak_topics": [_topic(row, db) for row in weak[:5]],
        "strong_topics": [_topic(row, db) for row in strong[:5]],
        "recommendations": recommendations,
    }


@router.get("/recommendations/summary")
def get_recommendation_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student(db, current_user)
    if not student:
        return {"weak_count": 0, "strong_count": 0, "recommendation_count": 0}
    rows = get_student_mastery(db, student.id)
    weak_count = len([row for row in rows if row.mastery_level in {"Needs Work", "Weak", "Improving"}])
    strong_count = len([row for row in rows if row.mastery_level in {"Strong", "Mastered"}])
    return {
        "weak_count": weak_count,
        "strong_count": strong_count,
        "recommendation_count": max(1, min(3, weak_count + strong_count)),
    }


@router.get("/learning-path")
def get_learning_path(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student(db, current_user)
    if not student:
        return {"overall_progress": 0, "estimated_completion_days": 0, "paths": []}
    rows = get_student_mastery(db, student.id)
    rows.sort(key=lambda row: row.mastery_score)
    progress = round(sum(row.mastery_score for row in rows) / len(rows), 1) if rows else 0
    paths = []
    for row in rows[:5]:
        current_level = "Advanced" if row.mastery_score >= 75 else "Intermediate" if row.mastery_score >= 55 else "Beginner"
        paths.append({
            "topic": row.topic,
            "current_level": current_level,
            "target_level": "Advanced",
            "estimated_days": max(1, round((85 - min(row.mastery_score, 85)) / 10)),
            "tasks": [
                f"Review core notes for {row.topic}",
                f"Take a focused quiz on {row.topic}",
                "Revise incorrect answers before moving on",
            ],
        })
    return {
        "overall_progress": progress,
        "estimated_completion_days": sum(path["estimated_days"] for path in paths),
        "paths": paths,
    }
