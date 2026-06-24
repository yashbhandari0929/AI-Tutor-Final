from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.explain import router as explain_router
from api.notes import router as notes_router
from api.quiz import router as quiz_router
from api.evaluate import router as evaluate_router
from api.student import router as student_router
from api.analytics import router as analytics_router
from api.videos import router as videos_router
from api.login import router as login_router
from api.weakness import router as weakness_router
from api.chat import router as chat_router
from api.flashcards import router as flash_router
from api.concepts import router as concept_router
from api.study_plan import router as study_router
from api.heatmap import router as heatmap_router
from api.auth import router as auth_router
from api.analytics_v2 import router as analytics_v2_router
from api.profile import router as profile_router
from api.dashboard import router as dashboard_router
from api.documents import router as documents_router
from api.conversations import router as conversations_router
from api.mastery import router as mastery_router
from api.interview import router as interview_router
from api.recommendations import router as recommendations_router

from database.database import engine
from database.models import Base
from database.migrations import ensure_sqlite_schema

# Create database tables
Base.metadata.create_all(bind=engine)
ensure_sqlite_schema(engine)

app = FastAPI(title="AI Tutor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router)
app.include_router(auth_router)
app.include_router(student_router)   # handles /students/*
app.include_router(explain_router)
app.include_router(notes_router)
app.include_router(quiz_router)
app.include_router(evaluate_router)
app.include_router(analytics_router)
app.include_router(analytics_v2_router)
app.include_router(profile_router)
app.include_router(dashboard_router)
app.include_router(documents_router)
app.include_router(conversations_router)
app.include_router(mastery_router)
app.include_router(interview_router)
app.include_router(recommendations_router)
app.include_router(videos_router)
app.include_router(weakness_router)
app.include_router(chat_router)
app.include_router(flash_router)
app.include_router(concept_router)
app.include_router(study_router)
app.include_router(heatmap_router)


@app.get("/")
def home():
    return {"message": "AI Tutor Backend Running"}
