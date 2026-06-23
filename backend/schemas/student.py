from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StudentCreate(BaseModel):
    name: str
    topic: Optional[str] = None
    level: Optional[str] = None


class StudentUpdateProgress(BaseModel):
    correct: int
    total: int


class StudentResponse(BaseModel):
    id: int
    name: str
    topic: Optional[str]
    level: Optional[str]
    accuracy: float
    total_quizzes: int
    correct_answers: int
    last_updated: datetime

    class Config:
        from_attributes = True