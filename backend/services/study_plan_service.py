"""
services/study_plan_service.py

AI-powered adaptive study plan engine.
Replaces the hardcoded bucket-based logic in the old study_plan.py and
dashboard.py. Every value is derived from real database rows; nothing is
fabricated. If data is genuinely sparse, the plan adapts gracefully.

Mastery formula (per topic):
  mastery = 0.40 * quiz_accuracy
           + 0.25 * consistency_score   (attempts spread across days)
           + 0.20 * completion_rate     (attempts / expected weekly cadence)
           + 0.15 * time_score          (normalised estimated minutes)

All scores are in [0, 100].
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    Document,
    Message,
    Note,
    QuizResult,
    StudentProfile,
)


# ── Data classes returned to the API layer ───────────────────────────────────

@dataclass
class TopicMastery:
    topic: str
    mastery_score: float          # 0-100
    quiz_accuracy: float          # raw average accuracy 0-100
    consistency_score: float      # 0-100
    completion_rate: float        # 0-100
    time_score: float             # 0-100
    attempts: int
    last_seen: Optional[date]
    trend: str                    # "improving" | "declining" | "stable" | "new"


@dataclass
class DailyTask:
    order: int
    task_type: str                # "quiz" | "notes" | "review" | "flashcard" | "mock"
    topic: str
    description: str
    estimated_minutes: int
    priority: str                 # "high" | "medium" | "low"
    difficulty: str               # "easy" | "medium" | "hard"


@dataclass
class WeeklyGoal:
    week_number: int              # 1-4 within rolling month
    focus_area: str
    target_accuracy: float
    topics: list[str]
    tasks_per_day: int
    milestone: str


@dataclass
class AdaptiveStudyPlan:
    # Snapshot
    overall_accuracy: float
    accuracy_tier: str            # "foundation" | "building" | "advancing" | "mastery"
    difficulty_level: str         # "easy" | "medium" | "hard" | "expert"

    # Topic classification
    weak_topics: list[TopicMastery]
    strong_topics: list[TopicMastery]
    all_mastery_scores: list[TopicMastery]

    # Plans
    daily_plan: list[DailyTask]
    weekly_plan: list[WeeklyGoal]

    # Meta
    recommendations: list[str]
    estimated_hours_to_next_tier: float
    estimated_completion_date: Optional[str]   # ISO date
    current_streak: int
    documents_available: int
    plan_generated_at: str                     # ISO datetime


# ── Constants ────────────────────────────────────────────────────────────────

TIER_THRESHOLDS = {
    "foundation": (0, 50),
    "building":   (50, 70),
    "advancing":  (70, 85),
    "mastery":    (85, 101),
}

TIER_DIFFICULTY = {
    "foundation": "easy",
    "building":   "medium",
    "advancing":  "hard",
    "mastery":    "expert",
}

# Approximate minutes per activity type (used for time estimates)
ACTIVITY_MINUTES = {
    "quiz":      20,
    "notes":     15,
    "review":    25,
    "flashcard": 10,
    "mock":      45,
}

# How many quiz attempts per week we consider "full completion"
EXPECTED_WEEKLY_ATTEMPTS = 5


# ── Internal helpers ─────────────────────────────────────────────────────────

def _accuracy_tier(avg: float) -> str:
    for tier, (lo, hi) in TIER_THRESHOLDS.items():
        if lo <= avg < hi:
            return tier
    return "mastery"


def _consistency_score(attempt_dates: list[date]) -> float:
    """
    Score how spread-out the attempts are over the last 30 days.
    100 = at least one attempt on every day of the past 4 weeks.
    0   = single burst on one day.
    """
    if not attempt_dates:
        return 0.0
    unique_days = len({d for d in attempt_dates if d >= date.today() - timedelta(days=30)})
    return min(unique_days / 20 * 100, 100)   # 20 unique days → 100


def _completion_rate(attempt_count: int) -> float:
    """Ratio of actual attempts to expected weekly cadence over 4 weeks."""
    expected = EXPECTED_WEEKLY_ATTEMPTS * 4
    return min(attempt_count / expected * 100, 100)


def _time_score(estimated_minutes: float) -> float:
    """Normalise against a 'good' benchmark of 120 min/topic over 4 weeks."""
    return min(estimated_minutes / 120 * 100, 100)


def _topic_mastery(
    topic: str,
    results: list[QuizResult],
    notes: list[Note],
) -> TopicMastery:
    topic_results = [r for r in results if (r.topic or "").lower() == topic.lower()]
    topic_notes   = [n for n in notes   if (n.topic or "").lower() == topic.lower()]

    if not topic_results:
        # Only notes, no quiz data yet
        return TopicMastery(
            topic=topic,
            mastery_score=5.0,
            quiz_accuracy=0.0,
            consistency_score=0.0,
            completion_rate=0.0,
            time_score=_time_score(len(topic_notes) * 10),
            attempts=0,
            last_seen=max((n.created_at.date() for n in topic_notes), default=None),
            trend="new",
        )

    accuracies   = [r.accuracy for r in topic_results if r.accuracy is not None]
    avg_acc      = sum(accuracies) / len(accuracies) if accuracies else 0.0
    attempt_dates = [r.created_at.date() for r in topic_results]
    consistency  = _consistency_score(attempt_dates)
    completion   = _completion_rate(len(topic_results))
    est_minutes  = len(topic_results) * ACTIVITY_MINUTES["quiz"] + len(topic_notes) * ACTIVITY_MINUTES["notes"]
    t_score      = _time_score(est_minutes)

    mastery = (
        0.40 * avg_acc
        + 0.25 * consistency
        + 0.20 * completion
        + 0.15 * t_score
    )

    # Trend: compare last 3 vs previous 3 attempts
    trend = "stable"
    if len(topic_results) >= 6:
        recent    = sorted(topic_results, key=lambda r: r.created_at)
        old_avg   = sum(r.accuracy or 0 for r in recent[:-3]) / (len(recent) - 3)
        new_avg   = sum(r.accuracy or 0 for r in recent[-3:]) / 3
        if new_avg - old_avg > 5:
            trend = "improving"
        elif old_avg - new_avg > 5:
            trend = "declining"
    elif len(topic_results) >= 1:
        trend = "new"

    return TopicMastery(
        topic=topic,
        mastery_score=round(mastery, 1),
        quiz_accuracy=round(avg_acc, 1),
        consistency_score=round(consistency, 1),
        completion_rate=round(completion, 1),
        time_score=round(t_score, 1),
        attempts=len(topic_results),
        last_seen=max(attempt_dates) if attempt_dates else None,
        trend=trend,
    )


def _build_daily_plan(
    tier: str,
    weak: list[TopicMastery],
    strong: list[TopicMastery],
    all_topics: list[TopicMastery],
    has_documents: bool,
    streak: int,
) -> list[DailyTask]:
    """
    Build 4-6 concrete tasks for today, ordered by priority.
    All topic names come from real DB records.
    """
    tasks: list[DailyTask] = []
    difficulty = TIER_DIFFICULTY[tier]
    order = 1

    def add(task_type: str, topic: str, description: str, priority: str, minutes: int | None = None):
        nonlocal order
        tasks.append(DailyTask(
            order=order,
            task_type=task_type,
            topic=topic,
            description=description,
            estimated_minutes=minutes or ACTIVITY_MINUTES[task_type],
            priority=priority,
            difficulty=difficulty,
        ))
        order += 1

    # No data at all → starter tasks using generic prompts
    if not all_topics:
        add("quiz",      "General",   "Take your first quiz to establish a baseline", "high")
        add("notes",     "General",   "Generate notes on a topic you're studying",    "high")
        add("flashcard", "General",   "Create flashcards for quick daily recall",     "medium")
        return tasks

    # 1. Weakest topic first (highest priority)
    if weak:
        w = weak[0]
        if tier == "foundation":
            add("notes",  w.topic, f"Study fundamentals of {w.topic} — mastery at {w.mastery_score:.0f}%",  "high")
            add("quiz",   w.topic, f"Take an easy quiz on {w.topic} to build confidence",                   "high")
        elif tier == "building":
            add("quiz",   w.topic, f"Medium-difficulty quiz on {w.topic} (accuracy {w.quiz_accuracy:.0f}%)", "high")
            add("review", w.topic, f"Review your incorrect answers in {w.topic}",                            "high")
        else:
            add("quiz",   w.topic, f"Hard quiz on {w.topic} to break the {w.quiz_accuracy:.0f}% ceiling",   "high")

    # 2. Second weakest topic
    if len(weak) >= 2:
        w2 = weak[1]
        add("notes", w2.topic, f"Generate condensed notes on {w2.topic} before tomorrow's quiz", "high")

    # 3. Declining topic intervention
    declining = [t for t in all_topics if t.trend == "declining"]
    if declining:
        d = declining[0]
        add("review", d.topic, f"Your {d.topic} accuracy is slipping — do a focused review today", "medium")

    # 4. RAG-based deep dive if documents uploaded
    if has_documents and weak:
        add("review", weak[0].topic,
            f"Chat with your uploaded documents about {weak[0].topic} concepts",
            "medium", minutes=30)

    # 5. Strong topic maintenance (don't let it decay)
    if strong and tier in ("advancing", "mastery"):
        s = strong[0]
        add("mock", s.topic, f"Timed mock test on {s.topic} to maintain {s.mastery_score:.0f}% mastery", "low")

    # 6. Streak motivation
    if streak == 0:
        tasks.insert(0, DailyTask(
            order=0, task_type="quiz", topic="Any",
            description="Start a new streak today — one quiz is all it takes",
            estimated_minutes=15, priority="high", difficulty="easy",
        ))
        for t in tasks[1:]:
            t.order += 1

    return tasks[:6]  # cap at 6 daily tasks


def _build_weekly_plan(
    tier: str,
    weak: list[TopicMastery],
    strong: list[TopicMastery],
    all_topics: list[TopicMastery],
    overall_accuracy: float,
) -> list[WeeklyGoal]:
    """
    Build a 4-week rolling plan. Every week has a concrete milestone
    tied to the user's real topic data.
    """
    goals: list[WeeklyGoal] = []
    tier_target = {"foundation": 50, "building": 70, "advancing": 85, "mastery": 95}
    next_target = tier_target.get(tier, 90)

    # Spread weak topics across weeks
    weak_names = [t.topic for t in weak[:8]]
    strong_names = [t.topic for t in strong[:4]]

    def week_topics(week: int) -> list[str]:
        chunk = weak_names[week * 2: week * 2 + 2]
        return chunk if chunk else (strong_names[:2] if strong_names else ["General"])

    milestones = [
        f"Reach {min(overall_accuracy + 5, next_target):.0f}% on your top weak topic",
        f"Complete 5 quizzes and review every incorrect answer",
        f"Achieve {min(overall_accuracy + 10, next_target):.0f}% average across all topics",
        f"Hit {next_target}% overall — unlock the next learning tier",
    ]

    focus_areas = {
        "foundation": ["Fundamental concepts", "Core vocabulary", "Foundational practice", "Baseline consolidation"],
        "building":   ["Targeted weak-topic drills", "Error analysis", "Mid-difficulty quizzes", "Accuracy push"],
        "advancing":  ["Hard-difficulty challenges", "Speed and accuracy", "Cross-topic integration", "Mock exams"],
        "mastery":    ["Expert-level problems", "Timed simulations", "Peer-level benchmarking", "Mastery retention"],
    }[tier]

    for i in range(4):
        goals.append(WeeklyGoal(
            week_number=i + 1,
            focus_area=focus_areas[i],
            target_accuracy=min(overall_accuracy + (i + 1) * 5, next_target),
            topics=week_topics(i),
            tasks_per_day=3 + (i % 2),
            milestone=milestones[i],
        ))

    return goals


def _recommendations(
    tier: str,
    weak: list[TopicMastery],
    strong: list[TopicMastery],
    streak: int,
    has_documents: bool,
) -> list[str]:
    recs: list[str] = []

    if weak:
        w = weak[0]
        recs.append(
            f"Your weakest topic is {w.topic} ({w.quiz_accuracy:.0f}% accuracy). "
            f"Quiz it daily until mastery exceeds 60%."
        )
        if w.trend == "declining":
            recs.append(
                f"{w.topic} accuracy is trending downward. Pause new topics and consolidate here first."
            )

    if tier == "foundation":
        recs += [
            "Focus exclusively on easy-difficulty quizzes until overall accuracy clears 50%.",
            "Generate notes before every quiz — reading first then testing doubles retention.",
        ]
    elif tier == "building":
        recs += [
            "You're in the growth zone. Aim for 3 medium-difficulty quizzes per day.",
            "Review every wrong answer immediately — don't move on until you understand the mistake.",
        ]
    elif tier == "advancing":
        recs += [
            "You're close to mastery. Hard quizzes on weak sub-topics will push you over 85%.",
            "Use the Analytics page to find the specific topics dragging your average down.",
        ]
    else:  # mastery
        recs += [
            "Outstanding accuracy. Shift to timed mock tests to sharpen recall under pressure.",
            "Help consolidate strong topics by attempting expert-level cross-topic problems.",
        ]

    if has_documents:
        recs.append("You have uploaded documents — ask the AI Tutor questions about them to deepen understanding.")

    if streak == 0:
        recs.append("You have no active streak. Even one quiz today restarts your momentum.")
    elif streak >= 7:
        recs.append(f"Impressive {streak}-day streak! Consistency at this stage compresses your time to mastery.")

    return recs[:6]


def _hours_to_next_tier(tier: str, overall_accuracy: float) -> float:
    """Rough estimate: each 1% of accuracy gain ≈ 45 min of focused study."""
    tier_ceiling = {"foundation": 50, "building": 70, "advancing": 85, "mastery": 100}
    gap = max(tier_ceiling.get(tier, 100) - overall_accuracy, 0)
    return round(gap * 0.75, 1)


def _estimated_completion_date(hours: float, streak: int) -> Optional[str]:
    if hours <= 0:
        return None
    daily_hours = 1.0 + (0.25 if streak > 0 else 0)   # active streak = more time
    days = math.ceil(hours / daily_hours)
    return (date.today() + timedelta(days=days)).isoformat()


# ── Public entry point ───────────────────────────────────────────────────────

def build_study_plan(db: Session, student: StudentProfile) -> AdaptiveStudyPlan:
    """
    Compute a fully personalised adaptive study plan for `student`.
    Reads: QuizResult, Note, Document, Message (for streak proxy).
    Never writes. Never raises for missing data — always returns a valid plan.
    """
    student_id = student.id

    # ── Pull raw data ────────────────────────────────────────────────────────
    all_results: list[QuizResult] = (
        db.query(QuizResult)
        .filter(QuizResult.student_id == student_id)
        .order_by(QuizResult.created_at.desc())
        .all()
    )
    all_notes: list[Note] = (
        db.query(Note)
        .filter(Note.student_id == student_id)
        .all()
    )
    doc_count: int = (
        db.query(func.count(Document.id))
        .filter(Document.student_id == student_id)
        .scalar() or 0
    )

    # Streak: consecutive days with any activity (quiz or note) up to today
    activity_dates: set[date] = set()
    for r in all_results:
        activity_dates.add(r.created_at.date())
    for n in all_notes:
        activity_dates.add(n.created_at.date())

    streak = 0
    check = date.today()
    while check in activity_dates:
        streak += 1
        check -= timedelta(days=1)

    # ── Overall accuracy ─────────────────────────────────────────────────────
    if all_results:
        overall_accuracy = round(
            sum(r.accuracy for r in all_results if r.accuracy is not None) / len(all_results),
            1,
        )
    else:
        overall_accuracy = 0.0

    tier = _accuracy_tier(overall_accuracy)

    # ── Topic mastery ────────────────────────────────────────────────────────
    all_topic_names: set[str] = set()
    for r in all_results:
        if r.topic:
            all_topic_names.add(r.topic)
    for n in all_notes:
        if n.topic:
            all_topic_names.add(n.topic)

    mastery_list: list[TopicMastery] = [
        _topic_mastery(t, all_results, all_notes) for t in sorted(all_topic_names)
    ]
    mastery_list.sort(key=lambda m: m.mastery_score)

    weak_topics   = [m for m in mastery_list if m.mastery_score < 60][:5]
    strong_topics = [m for m in reversed(mastery_list) if m.mastery_score >= 70][:5]

    # ── Plans ────────────────────────────────────────────────────────────────
    daily_plan = _build_daily_plan(
        tier, weak_topics, strong_topics, mastery_list,
        has_documents=(doc_count > 0),
        streak=streak,
    )
    weekly_plan = _build_weekly_plan(
        tier, weak_topics, strong_topics, mastery_list, overall_accuracy
    )

    recs = _recommendations(
        tier, weak_topics, strong_topics, streak, has_documents=(doc_count > 0)
    )

    hours = _hours_to_next_tier(tier, overall_accuracy)
    completion_date = _estimated_completion_date(hours, streak)

    return AdaptiveStudyPlan(
        overall_accuracy=overall_accuracy,
        accuracy_tier=tier,
        difficulty_level=TIER_DIFFICULTY[tier],
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        all_mastery_scores=mastery_list,
        daily_plan=daily_plan,
        weekly_plan=weekly_plan,
        recommendations=recs,
        estimated_hours_to_next_tier=hours,
        estimated_completion_date=completion_date,
        current_streak=streak,
        documents_available=doc_count,
        plan_generated_at=datetime.utcnow().isoformat(),
    )