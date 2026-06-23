from fastapi import APIRouter
from pydantic import BaseModel

from services.llm_service import generate_response

router = APIRouter()


class EvaluateRequest(BaseModel):
    topic: str
    total_questions: int
    correct_answers: int


@router.post("/quiz/evaluate")
def evaluate_quiz(data: EvaluateRequest):

    accuracy = round(
        (data.correct_answers / data.total_questions) * 100,
        2
    )

    prompt = f"""
    A student completed a quiz.

    Topic: {data.topic}

    Score: {data.correct_answers}/{data.total_questions}

    Accuracy: {accuracy}%

    Analyze the performance.

    Give:
    1. Understanding level
    2. Weak areas
    3. Improvement tips
    4. Recommended next difficulty
    """

    analysis = generate_response(prompt)

    return {
        "topic": data.topic,
        "score": data.correct_answers,
        "total_questions": data.total_questions,
        "accuracy": accuracy,
        "analysis": analysis
    }