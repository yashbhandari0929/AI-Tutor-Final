"""
services/stats_service.py

SINGLE SOURCE OF TRUTH for every statistic shown on the Dashboard,
Analytics, and Profile pages.

Why this file exists (audit finding): before this, accuracy/quiz counts/
notes counts were computed independently in api/profile.py,
api/analytics_v2.py, and api/student.py — three separate inline queries
that could (and did) drift apart, plus a fourth competing value cached
directly on StudentProfile (accuracy/total_quizzes/correct_answers) that
was hand-incremented by PUT /students/progress with no corresponding
QuizResult row. That's why different pages showed different numbers.

Rule going forward: QuizResult is the ledger. Nothing in this app should
trust StudentProfile's cached accuracy/total_quizzes/correct_answers
columns for *display* — they're kept only as a denormalized mirror,
recomputed from this module, never incremented independently.

Every function here takes `student_id` resolved server-side from the
JWT (via get_current_user → StudentProfile.user_id == current_user.id).
Nothing here ever takes a student_id from client input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    StudentProfile,
    QuizResult,
    Note,
    Document,
    Conversation,
    Message,
)


# ── Accuracy: the ONE formula used anywhere in this app ──────────────────────

def safe_accuracy(correct: float, total: float) -> float:
    """
    (correct / total) * 100. Returns 0.0 for zero/missing totals instead
    of raising ZeroDivisionError — a brand-new student with no attempts
    has 0% accuracy, not a 500 error.
    """
    if not total or total <= 0:
        return 0.0
    return round((correct / total) * 100, 2)


# ── Quiz stats ─────────────────────────────────────────────────────────────────

@dataclass
class QuizStats:
    total_attempts: int = 0        # number of QuizResult rows (quiz attempts)
    total_questions: int = 0       # sum of total_questions across attempts
    total_correct: int = 0         # sum of score across attempts
    average_accuracy: float = 0.0  # safe_accuracy(total_correct, total_questions)
    highest_score: int = 0


def get_quiz_stats(db: Session, student_id: int) -> QuizStats:
    row = (
        db.query(
            func.count(QuizResult.id),
            func.coalesce(func.sum(QuizResult.total_questions), 0),
            func.coalesce(func.sum(QuizResult.score), 0),
            func.coalesce(func.max(QuizResult.score), 0),
        )
        .filter(QuizResult.student_id == student_id)
        .one()
    )
    total_attempts, total_questions, total_correct, highest_score = row
    return QuizStats(
        total_attempts=total_attempts,
        total_questions=total_questions,
        total_correct=total_correct,
        average_accuracy=safe_accuracy(total_correct, total_questions),
        highest_score=highest_score,
    )


# ── Simple counts ──────────────────────────────────────────────────────────────

def get_notes_count(db: Session, student_id: int) -> int:
    return (
        db.query(func.count(Note.id))
        .filter(Note.student_id == student_id)
        .scalar()
        or 0
    )


def get_documents_count(db: Session, student_id: int) -> int:
    """Total documents uploaded by this student, global + per-conversation."""
    return (
        db.query(func.count(Document.id))
        .filter(Document.student_id == student_id)
        .scalar()
        or 0
    )


def get_conversations_count(db: Session, student_id: int) -> int:
    """
    'Total Study Sessions' = number of chat conversations (Conversation
    is the only session-like construct in the schema). If you also want
    quiz attempts and note generations counted as separate sessions,
    add get_quiz_stats().total_attempts + get_notes_count() to this.
    """
    return (
        db.query(func.count(Conversation.id))
        .filter(Conversation.student_id == student_id)
        .scalar()
        or 0
    )


def get_questions_asked_count(db: Session, student_id: int) -> int:
    """
    'Total Questions Asked' = number of user-authored chat messages
    across every conversation belonging to this student. This is
    DIFFERENT from quiz "questions answered" (see get_quiz_stats) —
    one is chat doubt-solving volume, the other is quiz question count.
    Always filtered through Conversation.student_id, never a raw
    Message query, so it can't cross into another user's chats.
    """
    return (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.student_id == student_id, Message.role == "user")
        .scalar()
        or 0
    )


# ── Topics studied (merged from Notes + Quizzes) ──────────────────────────────

def get_topics_studied(db: Session, student_id: int) -> list[str]:
    """
    Union of topics from Notes and QuizResults, deduplicated, oldest
    first appearance. Previously this only looked at Notes — a student
    who only ever took quizzes on a topic showed zero "topics studied".
    """
    rows: list[tuple[str, datetime]] = []
    rows += [
        (n.topic, n.created_at)
        for n in db.query(Note.topic, Note.created_at)
        .filter(Note.student_id == student_id, Note.topic.isnot(None))
        .all()
    ]
    rows += [
        (q.topic, q.created_at)
        for q in db.query(QuizResult.topic, QuizResult.created_at)
        .filter(QuizResult.student_id == student_id, QuizResult.topic.isnot(None))
        .all()
    ]
    rows.sort(key=lambda r: r[1] or datetime.min)

    seen: set[str] = set()
    topics: list[str] = []
    for topic, _ts in rows:
        if topic and topic not in seen:
            seen.add(topic)
            topics.append(topic)
    return topics


# ── Topic breakdown (accuracy per topic, for Analytics) ───────────────────────

def get_topic_breakdown(db: Session, student_id: int) -> list[dict]:
    rows = (
        db.query(QuizResult.topic, QuizResult.score, QuizResult.total_questions)
        .filter(QuizResult.student_id == student_id)
        .all()
    )
    agg: dict[str, dict] = {}
    for topic, score, total in rows:
        key = topic or "Unspecified"
        bucket = agg.setdefault(key, {"correct": 0, "total": 0, "attempts": 0})
        bucket["correct"] += score or 0
        bucket["total"] += total or 0
        bucket["attempts"] += 1

    return [
        {
            "topic": topic,
            "attempts": b["attempts"],
            "average_accuracy": safe_accuracy(b["correct"], b["total"]),
        }
        for topic, b in agg.items()
    ]


# ── Activity events (shared by streak, heatmap, weekly/monthly buckets) ───────

def get_all_activity_event_dates(db: Session, student_id: int) -> list[date]:
    """
    Flat (non-deduplicated) list of calendar dates, one per activity
    event: a quiz attempt, a note generated, a document uploaded, or a
    user chat message sent. This is the raw signal every time-bucketed
    stat below is built from.
    """
    out: list[date] = []

    out += [
        ts.date()
        for (ts,) in db.query(QuizResult.created_at)
        .filter(QuizResult.student_id == student_id)
        .all()
        if ts
    ]
    out += [
        ts.date()
        for (ts,) in db.query(Note.created_at)
        .filter(Note.student_id == student_id)
        .all()
        if ts
    ]
    out += [
        ts.date()
        for (ts,) in db.query(Document.uploaded_at)
        .filter(Document.student_id == student_id)
        .all()
        if ts
    ]
    out += [
        ts.date()
        for (ts,) in db.query(Message.created_at)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.student_id == student_id, Message.role == "user")
        .all()
        if ts
    ]
    return out


def get_current_streak(db: Session, student_id: int, today: Optional[date] = None) -> int:
    """
    Consecutive days of activity ending today or yesterday. If the most
    recent activity is more than 1 day old, the streak is 0 — a stale
    streak is reported as broken, not kept alive artificially.
    """
    today = today or datetime.utcnow().date()
    active_days = set(get_all_activity_event_dates(db, student_id))
    if not active_days:
        return 0

    most_recent = max(active_days)
    if (today - most_recent).days > 1:
        return 0

    streak = 0
    cursor = most_recent
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def get_activity_heatmap(db: Session, student_id: int, days: int = 180) -> dict[str, int]:
    """Date string (YYYY-MM-DD) -> activity count, for the last `days` days."""
    today = datetime.utcnow().date()
    start = today - timedelta(days=days - 1)
    counts: dict[str, int] = {
        (start + timedelta(days=i)).isoformat(): 0 for i in range(days)
    }
    for d in get_all_activity_event_dates(db, student_id):
        key = d.isoformat()
        if key in counts:
            counts[key] += 1
    return counts


def get_weekly_activity(db: Session, student_id: int, weeks: int = 8) -> list[dict]:
    """Activity count per ISO week, oldest first, for the last `weeks` weeks."""
    today = datetime.utcnow().date()
    current_week_start = today - timedelta(days=today.weekday())
    buckets: dict[date, int] = {
        current_week_start - timedelta(weeks=i): 0 for i in range(weeks)
    }
    for d in get_all_activity_event_dates(db, student_id):
        week_start = d - timedelta(days=d.weekday())
        if week_start in buckets:
            buckets[week_start] += 1
    return [
        {"week_start": k.isoformat(), "count": v} for k, v in sorted(buckets.items())
    ]


def get_monthly_activity(db: Session, student_id: int, months: int = 6) -> list[dict]:
    """Activity count per calendar month, oldest first, for the last `months` months."""
    today = datetime.utcnow().date()
    keys: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for i in range(months):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        keys.append((yy, mm))

    buckets: dict[str, int] = {f"{yy}-{mm:02d}": 0 for yy, mm in keys}
    for d in get_all_activity_event_dates(db, student_id):
        key = f"{d.year}-{d.month:02d}"
        if key in buckets:
            buckets[key] += 1
    return [{"month": k, "count": buckets[k]} for k in sorted(buckets.keys())]


def get_learning_trend(db: Session, student_id: int, weeks: int = 8) -> list[dict]:
    """
    Average quiz accuracy per week, oldest first — shows whether accuracy
    is trending up or down over time. Weeks with no quiz attempts show
    0.0 (no data), distinct from "trending down to 0%".
    """
    today = datetime.utcnow().date()
    current_week_start = today - timedelta(days=today.weekday())
    buckets: dict[date, dict] = {
        current_week_start - timedelta(weeks=i): {"correct": 0, "total": 0}
        for i in range(weeks)
    }
    rows = (
        db.query(QuizResult.created_at, QuizResult.score, QuizResult.total_questions)
        .filter(QuizResult.student_id == student_id)
        .all()
    )
    for ts, score, total in rows:
        if not ts:
            continue
        week_start = ts.date() - timedelta(days=ts.date().weekday())
        if week_start in buckets:
            buckets[week_start]["correct"] += score or 0
            buckets[week_start]["total"] += total or 0

    return [
        {
            "period": k.isoformat(),
            "average_accuracy": safe_accuracy(v["correct"], v["total"]),
        }
        for k, v in sorted(buckets.items())
    ]


# ── Study time (estimate — see docstring for the honest caveat) ───────────────

def get_estimated_study_minutes(
    db: Session, student_id: int, idle_cap_minutes: int = 5
) -> int:
    """
    ESTIMATE, not a tracked duration. The schema has no session
    start/end or duration field anywhere, so this sums the real gaps
    between a student's consecutive chat messages within each
    conversation, capping any single gap at `idle_cap_minutes` so a
    tab left open overnight doesn't inflate the total. Returns 0 for
    students with no multi-message conversations.

    If accurate study time matters, the real fix is a schema change:
    track explicit session start/end timestamps (e.g. on Conversation,
    or a dedicated StudySession table) rather than inferring it.
    """
    conversation_ids = [
        cid
        for (cid,) in db.query(Conversation.id)
        .filter(Conversation.student_id == student_id)
        .all()
    ]

    cap = timedelta(minutes=idle_cap_minutes)
    total_minutes = 0.0

    for conv_id in conversation_ids:
        timestamps = [
            ts
            for (ts,) in db.query(Message.created_at)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
            .all()
            if ts
        ]
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            total_minutes += min(gap, cap).total_seconds() / 60

    return round(total_minutes)