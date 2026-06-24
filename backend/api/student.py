from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from database.database import SessionLocal
from auth.security import decode_access_token
from database.models import StudentProfile, QuizResult, Note, User
from services import stats_service
from schemas.student import StudentCreate, StudentUpdateProgress, StudentResponse

router = APIRouter(prefix="/students", tags=["Students"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


def get_level(accuracy: float) -> str:
    """Derive a level label from a student's average accuracy."""
    if accuracy >= 90:
        return "Expert"
    elif accuracy >= 75:
        return "Advanced"
    elif accuracy >= 55:
        return "Intermediate"
    elif accuracy >= 35:
        return "Beginner"
    else:
        return "Novice"


def _student_from_auth_or_query(
    db: Session,
    authorization: str | None,
    student_id: int | None,
) -> StudentProfile | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id = int(payload.get("sub"))
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
                if student:
                    return student
        except Exception:
            pass
    if student_id is not None:
        return db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    return None


# Must be before /{student_id}
@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(StudentProfile).filter(
        StudentProfile.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    student = StudentProfile(
        name=payload.name,
        email=payload.email,
        password=payload.password,  # TODO: hash with bcrypt before production
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    return {
        "message": "Account created successfully",
        "student_id": student.id,
        "name": student.name,
        "email": student.email,
    }


# Must be before /{student_id}
@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    student = db.query(StudentProfile).filter(
        StudentProfile.email == payload.email
    ).first()
    if not student or student.password != payload.password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "message": "Login successful",
        "student_id": student.id,
        "name": student.name,
        "email": student.email,
    }


# Must be before /{student_id}
@router.get("/profile-info")
def get_profile_info(
    student_id: int | None = Query(None, description="Legacy student id fallback"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    student = _student_from_auth_or_query(db, authorization, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # ── Quiz stats ────────────────────────────────────────────────────────────
    quiz_stats = stats_service.get_quiz_stats(db, student.id)
    avg_accuracy = quiz_stats.average_accuracy
    total_quizzes = quiz_stats.total_attempts
    correct_answers = quiz_stats.total_correct

    # ── Level derived from accuracy (not stored value) ────────────────────────
    computed_level = get_level(avg_accuracy)

    # ── Topics from Notes (unique, preserving insertion order) ────────────────
    notes = (
        db.query(Note)
        .filter(Note.student_id == student.id)
        .order_by(Note.created_at)
        .all()
    )
    seen: set = set()
    topics_from_notes: list[str] = []
    for note in notes:
        if note.topic and note.topic not in seen:
            seen.add(note.topic)
            topics_from_notes.append(note.topic)

    return {
        "student_id": student.id,
        "name": student.name,
        "email": student.email,
        "joined": student.created_at,
        "topic": student.topic,
        # level is now always computed from accuracy, never read from DB
        "level": computed_level,
        "accuracy": round(avg_accuracy, 2),
        "total_quizzes": total_quizzes,
        "correct_answers": correct_answers,
        # new field: list of unique topics the student has generated notes for
        "notes_topics": topics_from_notes,
        "topics_studied": stats_service.get_topics_studied(db, student.id),
        "total_questions_asked": stats_service.get_questions_asked_count(db, student.id),
        "total_study_sessions": stats_service.get_conversations_count(db, student.id),
        "total_documents_uploaded": stats_service.get_documents_count(db, student.id),
        "current_streak": stats_service.get_current_streak(db, student.id),
    }


@router.post("/", response_model=StudentResponse)
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    student = StudentProfile(
        name=data.name,
        topic=data.topic,
        level=data.level,
        accuracy=0.0,
        total_quizzes=0,
        correct_answers=0,
        last_updated=datetime.utcnow(),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.put("/{student_id}/progress", response_model=StudentResponse)
def update_progress(
    student_id: int,
    data: StudentUpdateProgress,
    db: Session = Depends(get_db),
):
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.correct_answers += data.correct or 0
    student.total_quizzes += data.total or 0
    student.accuracy = (
        (student.correct_answers / student.total_quizzes) * 100
        if student.total_quizzes > 0 else 0.0
    )
    student.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(student)
    return student


# Keep LAST — wildcard swallows any route defined after it
@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
