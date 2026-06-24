from datetime import datetime
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.security import decode_access_token
from database.database import SessionLocal
from database.models import Quiz, QuizResult, StudentProfile, User
from services import stats_service
from services.llm_service import generate_response
from services.topic_mastery_service import update_mastery_from_quiz_result

router = APIRouter()
logger = logging.getLogger(__name__)


class QuizRequest(BaseModel):
    topic: str
    difficulty: str
    questions: int


class QuizResultRequest(BaseModel):
    topic: str
    score: int
    total_questions: int
    student_id: int | None = None
    answers: list[dict] = Field(default_factory=list)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _student_from_auth(
    db: Session,
    authorization: str | None,
    fallback_student_id: int | None = None,
) -> StudentProfile | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id = int(payload.get("sub"))
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
        except Exception:
            pass
    if fallback_student_id is not None:
        return db.query(StudentProfile).filter(StudentProfile.id == fallback_student_id).first()
    return db.query(StudentProfile).first()


@router.post("/quiz/generate")
def generate_quiz(
    data: QuizRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    prompt = f"""
Generate {data.questions} MCQ questions.

Topic: {data.topic}
Difficulty: {data.difficulty}

Return ONLY a valid JSON array. Each item must have:
question, options, correctAnswer, explanation.
correctAnswer must be the zero-based index of the correct option.
"""
    quiz = generate_response(prompt)

    db_quiz = Quiz(topic=data.topic, difficulty=data.difficulty, questions=quiz or "[]")
    db.add(db_quiz)

    student = _student_from_auth(db, authorization)
    if student:
        student.quizzes_generated = (student.quizzes_generated or 0) + 1
        student.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(db_quiz)

    return {
        "topic": data.topic,
        "difficulty": data.difficulty,
        "quiz": quiz or "[]",
    }


@router.post("/quiz/result")
def save_result(
    data: QuizResultRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    total_questions = max(data.total_questions or 0, 0)
    score = min(max(data.score or 0, 0), total_questions)
    accuracy = (score / total_questions) * 100 if total_questions else 0.0
    student = _student_from_auth(db, authorization, data.student_id)
    topic = (data.topic or "General").strip() or "General"

    if total_questions <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_questions must be greater than zero.",
        )

    answers = data.answers or []
    correct_answers = [item for item in answers if item.get("is_correct") is True]
    incorrect_answers = [item for item in answers if item.get("is_correct") is False]
    explanations = [
        {
            "question": item.get("question"),
            "correct_answer": item.get("correct_answer"),
            "explanation": item.get("explanation") or "No explanation was provided for this question.",
        }
        for item in answers
    ]

    try:
        result = QuizResult(
            student_id=student.id if student else data.student_id,
            topic=topic,
            score=score,
            total_questions=total_questions,
            accuracy=round(accuracy, 2),
            details_json=json.dumps(answers),
        )
        db.add(result)
        db.flush()

        if student:
            quiz_stats = stats_service.get_quiz_stats(db, student.id)
            student.total_quizzes = quiz_stats.total_attempts
            student.correct_answers = quiz_stats.total_correct
            student.accuracy = quiz_stats.average_accuracy
            student.last_updated = datetime.utcnow()
            mastery = update_mastery_from_quiz_result(db, result)
        else:
            mastery = None

        db.commit()
        db.refresh(result)
        return {
            "message": "Result saved.",
            "result_id": result.id,
            "topic": result.topic,
            "score": result.score,
            "total_questions": result.total_questions,
            "percentage": result.accuracy,
            "accuracy": result.accuracy,
            "correct_count": len(correct_answers) if answers else score,
            "incorrect_count": len(incorrect_answers) if answers else total_questions - score,
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "explanations": explanations,
            "mastery": {
                "topic": mastery.topic,
                "attempts": mastery.attempts,
                "correct_answers": mastery.correct_answers,
                "accuracy": mastery.accuracy,
                "mastery_score": mastery.mastery_score,
                "mastery_level": mastery.mastery_level,
            } if mastery else None,
        }
    except Exception:
        db.rollback()
        logger.exception("Failed to save quiz result topic=%s student_id=%s", topic, student.id if student else data.student_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save quiz result. Check server logs for details.",
        )
