from fastapi import APIRouter
from database.database import SessionLocal
from database.models import QuizResult

router = APIRouter()


@router.get("/study-plan")
def study_plan():

    db = SessionLocal()
    results = db.query(QuizResult).all()
    db.close()

    total = len(results)

    if total == 0:
        return {
            "plan": [
                "Start with basic quizzes",
                "Generate notes for topics",
                "Take first assessment"
            ]
        }

    avg = sum(r.accuracy for r in results) / total

    plan = []

    if avg < 30:
        plan = [
            "📘 Revise fundamentals",
            "🧠 Watch beginner videos",
            "📝 Generate notes daily",
            "🎯 Take easy quizzes only"
        ]

    elif avg < 60:
        plan = [
            "📗 Focus weak topics",
            "🧪 Practice medium quizzes",
            "📊 Review mistakes",
            "📚 Use flashcards daily"
        ]

    elif avg < 80:
        plan = [
            "📘 Attempt hard quizzes",
            "🧠 Improve weak topics",
            "🎥 Watch advanced videos",
            "📈 Track mistakes"
        ]

    else:
        plan = [
            "🚀 Advanced problem solving",
            "🏆 Mock tests",
            "📊 Optimize speed",
            "🔥 Maintain consistency"
        ]

    return {
        "average_accuracy": round(avg, 2),
        "plan": plan
    }