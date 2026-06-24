from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database.database import SessionLocal
from database.models import InterviewQuestion, InterviewSession, StudentProfile, User
from services.interview_service import (
    analyze_resume,
    evaluate_answer,
    generate_questions,
    interview_analytics,
    question_to_dict,
    session_report,
    session_to_analysis,
)

router = APIRouter(prefix="/interview", tags=["Resume Interview Prep"])


class GenerateQuestionsRequest(BaseModel):
    session_id: int
    difficulty: str = "Medium"


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    session_id: int | None = None
    question_id: int | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _student(db: Session, user: User) -> StudentProfile:
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return student


def _session(db: Session, student_id: int, session_id: int) -> InterviewSession:
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id, InterviewSession.student_id == student_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session


async def _upload_resume_impl(
    file: UploadFile,
    current_user: User,
    db: Session,
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF resumes are supported.",
        )
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded resume is empty.")
    student = _student(db, current_user)
    try:
        session = analyze_resume(file_bytes, file.filename or "resume.pdf", student.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return session_to_analysis(session)


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _upload_resume_impl(file, current_user, db)


@router.post("/upload")
async def upload_resume_alias(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _upload_resume_impl(file, current_user, db)


def _generate_questions_impl(
    data: GenerateQuestionsRequest,
    current_user: User,
    db: Session,
):
    student = _student(db, current_user)
    session = _session(db, student.id, data.session_id)
    questions = generate_questions(session, data.difficulty, db)
    return {
        "session_id": session.id,
        "questions": [question_to_dict(question) for question in questions],
    }


@router.post("/generate-questions")
def generate_interview_questions(
    data: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_questions_impl(data, current_user, db)


@router.post("/generate")
def generate_interview_questions_alias(
    data: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_questions_impl(data, current_user, db)


def _evaluate_answer_impl(
    data: EvaluateAnswerRequest,
    current_user: User,
    db: Session,
):
    student = _student(db, current_user)
    session_id = data.session_id
    if session_id is None and data.question_id is not None:
        question = (
            db.query(InterviewQuestion)
            .join(InterviewSession, InterviewQuestion.session_id == InterviewSession.id)
            .filter(
                InterviewQuestion.id == data.question_id,
                InterviewSession.student_id == student.id,
            )
            .first()
        )
        session_id = question.session_id if question else None
    if session_id is None:
        latest = (
            db.query(InterviewSession)
            .filter(InterviewSession.student_id == student.id)
            .order_by(InterviewSession.created_at.desc())
            .first()
        )
        session_id = latest.id if latest else None
    if session_id is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    session = _session(db, student.id, session_id)
    return evaluate_answer(session, data.question, data.answer, db, data.question_id)


@router.post("/evaluate-answer")
def evaluate_interview_answer(
    data: EvaluateAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _evaluate_answer_impl(data, current_user, db)


@router.post("/evaluate")
def evaluate_interview_answer_alias(
    data: EvaluateAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _evaluate_answer_impl(data, current_user, db)


@router.get("/report")
def get_report(
    session_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student(db, current_user)
    query = db.query(InterviewSession).filter(InterviewSession.student_id == student.id)
    if session_id is not None:
        session = query.filter(InterviewSession.id == session_id).first()
    else:
        session = query.order_by(InterviewSession.created_at.desc()).first()
    if not session:
        return {
            "readiness_score": 0,
            "weak_skill_areas": [],
            "recommended_topics": [],
            "questions": [],
            "answers": [],
        }
    return session_report(session)


@router.get("/history")
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student(db, current_user)
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.student_id == student.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return {"sessions": [session_report(session) for session in sessions]}


@router.get("/analytics")
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _student(db, current_user)
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.student_id == student.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return interview_analytics(sessions)
