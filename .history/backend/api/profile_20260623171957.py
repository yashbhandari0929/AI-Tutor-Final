from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import User, StudentProfile
from auth.dependencies import get_current_user
from schemas.profile_analytics import ProfileResponse
from services import stats_service

router = APIRouter(prefix="/profile", tags=["Profile"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the logged-in user's own profile. No student_id query param —
    identity comes entirely from the JWT via get_current_user.

    AUDIT FIX: this used to run its own inline
    `sum(q.accuracy for q in quizzes) / total_quizzes` query, a second,
    independent accuracy calculation living alongside the one in
    api/analytics_v2.py and api/student.py. Replaced with
    stats_service.get_quiz_stats so this endpoint is guaranteed to agree
    with every other page, even if it isn't currently called by the
    frontend (verify this before relying on it — if it's truly unused,
    consider removing it instead of maintaining a fourth route that
    returns the same numbers as /students/profile-info).
    """
    student = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this account.",
        )

    quiz_stats = stats_service.get_quiz_stats(db, student.id)

    return ProfileResponse(
        name=student.name,
        email=current_user.email,
        created_at=current_user.created_at,
        total_quizzes=quiz_stats.total_attempts,
        accuracy=quiz_stats.average_accuracy,
    )