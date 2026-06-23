from fastapi import APIRouter
from services.llm_service import generate_response
import json

router = APIRouter()


@router.get("/concept-graph")
def concept_graph(topic: str):

    prompt = f"""
Create a learning dependency graph for:

Topic: {topic}

Return ONLY valid JSON like this:

[
  {{"from": "Basics", "to": "Intermediate"}},
  {{"from": "Intermediate", "to": "Advanced"}}
]

No explanation, no markdown.
"""

    result = generate_response(prompt)

    try:
        # clean + force JSON safety
        cleaned = result.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        return {"graph": parsed}

    except Exception:
        return {
            "graph": [
                {"from": "Basics", "to": "Intermediate"},
                {"from": "Intermediate", "to": "Advanced"}
            ]
        }