from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_service import generate_response

router = APIRouter()


class FlashcardRequest(BaseModel):
    topic: str


@router.post("/flashcards")
def generate_flashcards(data: FlashcardRequest):

    prompt = f"""
Create flashcards for:

Topic: {data.topic}

Return JSON only:

[
  {{
    "question": "What is ...?",
    "answer": "..."
  }}
]

No explanation.
"""

    result = generate_response(prompt)

    return {
        "flashcards": result
    }