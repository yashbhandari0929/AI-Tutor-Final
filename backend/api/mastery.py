from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database.database import SessionLocal
from database.models import User, StudentProfile
from services.topic_mastery_service import get_student_mastery, mastery_summary

router = APIRouter(prefix="/mastery", tags=["Topic Mastery"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _student_for_user(db: Session, user: User) -> StudentProfile | None:
    return db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()


def _out(row):
    return {
        "id": row.id,
        "student_id": row.student_id,
        "topic": row.topic,
        "attempts": row.attempts,
        "correct_answers": row.correct_answers,
        "accuracy": row.accuracy,
        "mastery_score": row.mastery_score,
        "mastery_level": row.mastery_level,
        "last_practiced": row.last_practiced.isoformat() if row.last_practiced else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
def list_mastery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student_for_user(db, current_user)
    if not student:
        return []
    return [_out(row) for row in get_student_mastery(db, student.id)]


@router.get("/summary")
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student_for_user(db, current_user)
    if not student:
        return mastery_summary([])
    return mastery_summary(get_student_mastery(db, student.id))


@router.get("/weak-topics")
def get_weak_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student_for_user(db, current_user)
    if not student:
        return []
    rows = [
        row for row in get_student_mastery(db, student.id)
        if row.mastery_level in {"Needs Work", "Weak", "Improving"}
    ]
    rows.sort(key=lambda row: (row.mastery_score, row.accuracy, row.topic))
    return [_out(row) for row in rows[:10]]


@router.get("/strong-topics")
def get_strong_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student_for_user(db, current_user)
    if not student:
        return []
    rows = [
        row for row in get_student_mastery(db, student.id)
        if row.mastery_level in {"Strong", "Mastered"}
    ]
    rows.sort(key=lambda row: (-row.mastery_score, -row.accuracy, row.topic))
    return [_out(row) for row in rows[:10]]
