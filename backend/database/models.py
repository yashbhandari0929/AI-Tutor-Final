from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from database.database import Base


class StudentProfile(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)

    # Auth
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # TODO: hash with bcrypt before production

    # Identity
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Learning
    topic = Column(String)
    level = Column(String)

    # Stats
    accuracy = Column(Float, default=0)
    total_quizzes = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    notes_generated = Column(Integer, default=0)
    quizzes_generated = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String)
    difficulty = Column(String)
    questions = Column(String)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    topic = Column(String)
    score = Column(Integer)
    total_questions = Column(Integer)
    accuracy = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── NEW ──────────────────────────────────────────────────────────────────────
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    subject = Column(String)          # e.g. "Science"
    topic = Column(String)            # e.g. "Photosynthesis"
    level = Column(String)            # difficulty level used when generating
    created_at = Column(DateTime, default=datetime.utcnow)