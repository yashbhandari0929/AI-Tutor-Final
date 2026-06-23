from fastapi import APIRouter
from pydantic import BaseModel

from services.llm_service import generate_response

router = APIRouter()


class ExplainRequest(BaseModel):
    topic: str
    level: str


@router.post("/explain")
def explain_topic(data: ExplainRequest):

    prompt = f"""
    You are an expert AI tutor.

    Explain {data.topic}
    for a {data.level} student.

    Use:
    - Simple language
    - Real-life examples
    - Bullet points
    - Summary at the end
    """

    answer = generate_response(prompt)

    return {
        "topic": data.topic,
        "level": data.level,
        "answer": answer
    }