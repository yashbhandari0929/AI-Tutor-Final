from fastapi import APIRouter
from database.database import SessionLocal
from database.models import QuizResult
from collections import defaultdict

router = APIRouter()


@router.get("/heatmap")
def heatmap():

    db = SessionLocal()
    results = db.query(QuizResult).all()
    db.close()

    activity = defaultdict(int)

    for r in results:
        date = r.created_at.date().isoformat()
        activity[date] += 1

    return {
        "activity": activity
    }