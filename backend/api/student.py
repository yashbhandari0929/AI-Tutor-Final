from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from database.database import SessionLocal
from database.models import StudentProfile, QuizResult, Note
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
    student_id: int = Query(..., description="ID of the logged-in student"),
    db: Session = Depends(get_db),
):
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # ── Quiz stats ────────────────────────────────────────────────────────────
    quizzes = db.query(QuizResult).filter(QuizResult.student_id == student_id).all()
    total_quizzes = len(quizzes)
    avg_accuracy = 0.0
    correct_answers = 0

    if total_quizzes > 0:
        avg_accuracy = sum(q.accuracy for q in quizzes) / total_quizzes
        correct_answers = sum(q.score for q in quizzes)

    # ── Level derived from accuracy (not stored value) ────────────────────────
    computed_level = get_level(avg_accuracy)

    # ── Topics from Notes (unique, preserving insertion order) ────────────────
    notes = (
        db.query(Note)
        .filter(Note.student_id == student_id)
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