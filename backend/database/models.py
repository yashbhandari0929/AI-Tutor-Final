from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, synonym

from database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)


class StudentProfile(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True, index=True)

    # Legacy auth fields are kept nullable for backward compatibility with
    # /students/register and older local databases.
    email = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=True)

    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    topic = Column(String)
    level = Column(String)

    accuracy = Column(Float, default=0)
    total_quizzes = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    notes_generated = Column(Integer, default=0)
    quizzes_generated = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="student_profile")
    quiz_results = relationship("QuizResult", back_populates="student")
    notes = relationship("Note", back_populates="student")
    conversations = relationship("Conversation", back_populates="student")
    documents = relationship("Document", back_populates="student")
    topic_mastery = relationship("StudentTopicMastery", back_populates="student")
    interview_sessions = relationship("InterviewSession", back_populates="student")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String)
    difficulty = Column(String)
    questions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    topic = Column(String, index=True)
    score = Column(Integer)
    total_questions = Column(Integer)
    accuracy = Column(Float)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="quiz_results")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    subject = Column(String)
    topic = Column(String)
    level = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="notes")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String, default="New Chat", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("StudentProfile", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    attachments = relationship("Document", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    used_rag = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    source = Column(String, default="pdf_upload")
    file_type = Column(String, default="pdf", nullable=False)
    file_path = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("StudentProfile", back_populates="documents")
    conversation = relationship("Conversation", back_populates="attachments")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    chunk_text = synonym("text")
    embedding_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="chunks")


class StudentTopicMastery(Base):
    __tablename__ = "student_topic_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "topic", name="uq_student_topic_mastery_student_topic"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    topic = Column(String, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    accuracy = Column(Float, default=0.0, nullable=False)
    mastery_score = Column(Float, default=0.0, nullable=False)
    mastery_level = Column(String, default="Needs Work", nullable=False)
    last_practiced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("StudentProfile", back_populates="topic_mastery")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    resume_name = Column(String, nullable=False)
    resume_text = Column(Text, default="")
    name = Column(String, default="")
    resume_score = Column(Float, default=0.0)
    ats_score = Column(Float, default=0.0)
    skills = Column(Text, default="[]")
    projects = Column(Text, default="[]")
    experience = Column(Text, default="[]")
    education = Column(Text, default="[]")
    skill_gap_analysis = Column(Text, default="[]")
    strengths = Column(Text, default="[]")
    improvements = Column(Text, default="[]")
    readiness_score = Column(Float, default=0.0)
    weak_skill_areas = Column(Text, default="[]")
    recommended_topics = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("StudentProfile", back_populates="interview_sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    difficulty = Column(String, default="Medium", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("InterviewSession", back_populates="questions")
    answers = relationship("InterviewAnswer", back_populates="question")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=True, index=True)
    answer = Column(Text, nullable=False)
    feedback = Column(Text, default="")
    strengths = Column(Text, default="[]")
    weaknesses = Column(Text, default="[]")
    suggested_improvement = Column(Text, default="")
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("InterviewSession", back_populates="answers")
    question = relationship("InterviewQuestion", back_populates="answers")
