from fastapi import APIRouter
from pydantic import BaseModel
import json
from database.models import QuizResult
from services.llm_service import generate_response
from database.database import SessionLocal
from database.models import Quiz
from datetime import datetime
from database.models import (
    QuizResult,
    StudentProfile
)

router = APIRouter()

class QuizRequest(BaseModel):
    topic: str
    difficulty: str
    questions: int

class QuizResultRequest(BaseModel):
    topic: str
    score: int
    total_questions: int


@router.post("/quiz/generate")
def generate_quiz(data: QuizRequest):

    prompt = f"""
Generate {data.questions} MCQ questions.

Topic: {data.topic}
Difficulty: {data.difficulty}

Return ONLY valid JSON array.
"""

    quiz = generate_response(prompt)

    # ✅ SAVE TO DB
    db = SessionLocal()
    db_quiz = Quiz(
        topic=data.topic,
        difficulty=data.difficulty,
        questions=quiz
    )
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)
    db.close()

    return {
        "topic": data.topic,
        "difficulty": data.difficulty,
        "quiz": quiz
    }


@router.post("/quiz/result")
def save_result(data: QuizResultRequest):

    accuracy = (
        data.score /
        data.total_questions
    ) * 100

    db = SessionLocal()

    try:

        # Save quiz result
        result = QuizResult(
            topic=data.topic,
            score=data.score,
            total_questions=data.total_questions,
            accuracy=accuracy
        )

        db.add(result)

        # Get student profile
        student = db.query(
            StudentProfile
        ).first()

        if student:

            student.total_quizzes += 1

            student.correct_answers += data.score

            total_possible_answers = (
                student.total_quizzes *
                data.total_questions
            )

            if total_possible_answers > 0:
                student.accuracy = (
                    student.correct_answers /
                    total_possible_answers
                ) * 100

            student.last_updated = datetime.utcnow()

        db.commit()

        return {
            "message": "Result Saved"
        }

    except Exception as e:

        db.rollback()

        return {
            "error": str(e)
        }

    finally:
        db.close()