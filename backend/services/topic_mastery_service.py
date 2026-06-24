from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from database.models import QuizResult, StudentProfile, StudentTopicMastery

MASTERY_LEVELS = ("Needs Work", "Weak", "Improving", "Strong", "Mastered")


def mastery_level(score: float) -> str:
    if score >= 90:
        return "Mastered"
    if score >= 75:
        return "Strong"
    if score >= 55:
        return "Improving"
    if score >= 35:
        return "Weak"
    return "Needs Work"


def mastery_score(accuracy: float, attempts: int) -> float:
    practice_bonus = min(attempts / 40 * 20, 20)
    return round(min((accuracy * 0.8) + practice_bonus, 100), 2)


def recalculate_topic_mastery(
    db: Session,
    student_id: int,
    topic: str,
) -> StudentTopicMastery:
    clean_topic = (topic or "General").strip() or "General"
    results = (
        db.query(QuizResult)
        .filter(
            QuizResult.student_id == student_id,
            QuizResult.topic == clean_topic,
        )
        .order_by(QuizResult.created_at.asc())
        .all()
    )

    attempts = sum(result.total_questions or 0 for result in results)
    correct = sum(result.score or 0 for result in results)
    accuracy = round((correct / attempts) * 100, 2) if attempts else 0.0
    score = mastery_score(accuracy, attempts)
    level = mastery_level(score)
    last_practiced = max((result.created_at for result in results if result.created_at), default=None)

    row = (
        db.query(StudentTopicMastery)
        .filter(
            StudentTopicMastery.student_id == student_id,
            StudentTopicMastery.topic == clean_topic,
        )
        .first()
    )
    if not row:
        row = StudentTopicMastery(student_id=student_id, topic=clean_topic)
        db.add(row)

    row.attempts = attempts
    row.correct_answers = correct
    row.accuracy = accuracy
    row.mastery_score = score
    row.mastery_level = level
    row.last_practiced = last_practiced
    row.updated_at = datetime.utcnow()
    db.flush()
    return row


def update_mastery_from_quiz_result(db: Session, result: QuizResult) -> StudentTopicMastery | None:
    if not result.student_id or not result.topic:
        return None
    return recalculate_topic_mastery(db, result.student_id, result.topic)


def rebuild_student_mastery(db: Session, student_id: int) -> list[StudentTopicMastery]:
    topics = [
        topic
        for (topic,) in db.query(QuizResult.topic)
        .filter(QuizResult.student_id == student_id, QuizResult.topic.isnot(None))
        .distinct()
        .all()
        if topic
    ]
    return [recalculate_topic_mastery(db, student_id, topic) for topic in topics]


def get_student_mastery(db: Session, student_id: int) -> list[StudentTopicMastery]:
    rows = (
        db.query(StudentTopicMastery)
        .filter(StudentTopicMastery.student_id == student_id)
        .order_by(StudentTopicMastery.mastery_score.asc(), StudentTopicMastery.topic.asc())
        .all()
    )
    if rows:
        return rows
    return rebuild_student_mastery(db, student_id)


def get_or_create_student_for_user(db: Session, user_id: int) -> StudentProfile | None:
    return db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()


def mastery_summary(rows: list[StudentTopicMastery]) -> dict:
    distribution = {level: 0 for level in MASTERY_LEVELS}
    for row in rows:
        distribution[row.mastery_level] = distribution.get(row.mastery_level, 0) + 1

    total_attempts = sum(row.attempts or 0 for row in rows)
    total_correct = sum(row.correct_answers or 0 for row in rows)
    average_accuracy = round((total_correct / total_attempts) * 100, 2) if total_attempts else 0.0
    last_practiced = max((row.last_practiced for row in rows if row.last_practiced), default=None)

    return {
        "total_topics": len(rows),
        "total_attempts": total_attempts,
        "total_correct_answers": total_correct,
        "average_accuracy": average_accuracy,
        "mastered_topics": distribution["Mastered"],
        "strong_topics": distribution["Strong"],
        "improving_topics": distribution["Improving"],
        "weak_topics": distribution["Weak"],
        "needs_work_topics": distribution["Needs Work"],
        "mastery_distribution": distribution,
        "last_practiced": last_practiced.isoformat() if last_practiced else None,
    }
