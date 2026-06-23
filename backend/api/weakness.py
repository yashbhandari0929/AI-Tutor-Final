from fastapi import APIRouter
from database.database import SessionLocal
from database.models import QuizResult
from collections import defaultdict

router = APIRouter()


@router.get("/weak-topics")
def weak_topics():

    db = SessionLocal()
    results = db.query(QuizResult).all()
    db.close()

    topic_data = defaultdict(lambda: {"score": 0, "count": 0})

    for r in results:
        topic_data[r.topic]["score"] += r.score
        topic_data[r.topic]["count"] += r.total_questions

    weak_topics = []

    for topic, data in topic_data.items():
        if data["count"] == 0:
            continue

        accuracy = (data["score"] / data["count"]) * 100

        if accuracy < 60:
            weak_topics.append({
                "topic": topic,
                "accuracy": round(accuracy, 2)
            })

    return {
        "weak_topics": weak_topics
    }