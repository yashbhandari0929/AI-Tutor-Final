from fastapi import APIRouter
from database.database import SessionLocal
from database.models import QuizResult

router = APIRouter()


@router.get("/analytics")
def get_analytics():

    db = SessionLocal()

    quizzes = db.query(
        QuizResult
    ).all()

    total_quizzes = len(quizzes)

    avg_accuracy = 0
    highest_score = 0
    total_correct = 0
    total_questions = 0

    score_history = []

    topic_stats = {}

    if total_quizzes > 0:

        avg_accuracy = (
            sum(q.accuracy for q in quizzes)
            / total_quizzes
        )

        highest_score = max(
            q.score for q in quizzes
        )

        total_correct = sum(
            q.score for q in quizzes
        )

        total_questions = sum(
            q.total_questions for q in quizzes
        )

        for index, quiz in enumerate(quizzes):

            score_history.append({
                "quiz": f"Quiz {index + 1}",
                "accuracy": round(
                    quiz.accuracy,
                    2
                )
            })

            if quiz.topic not in topic_stats:
                topic_stats[
                    quiz.topic
                ] = []

            topic_stats[
                quiz.topic
            ].append(
                quiz.accuracy
            )

    weakest_topic = "N/A"

    if topic_stats:

        topic_avg = {
            topic:
            sum(scores) / len(scores)
            for topic, scores
            in topic_stats.items()
        }

        weakest_topic = min(
            topic_avg,
            key=topic_avg.get
        )

    db.close()

    return {
        "total_quizzes": total_quizzes,
        "average_accuracy": round(
            avg_accuracy,
            2
        ),
        "highest_score": highest_score,
        "correct_answers": total_correct,
        "total_questions": total_questions,
        "weakest_topic": weakest_topic,
        "score_history": score_history
    }
"""
The following JavaScript/TypeScript helper was present in the file
and has been converted to a string to avoid syntax errors in Python.

const getAnalysis = (accuracy: number) => {

  if (accuracy <= 30)
    return {
      level: "Needs Improvement",
      advice: [
        "Review fundamentals",
        "Generate more notes",
        "Attempt easy quizzes first",
        "Practice daily"
      ]
    };

  if (accuracy <= 60)
    return {
      level: "Average",
      advice: [
        "Revise weak topics",
        "Increase quiz frequency",
        "Focus on mistakes"
      ]
    };

  if (accuracy <= 80)
    return {
      level: "Good",
      advice: [
        "Move to harder quizzes",
        "Strengthen weak areas",
        "Keep practicing"
      ]
    };

  return {
    level: "Excellent",
    advice: [
      "Ready for advanced topics",
      "Maintain consistency",
      "Challenge yourself"
    ]
  };
};
"""