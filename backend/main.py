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

from database.database import engine
from database.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Tutor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router)
app.include_router(student_router)   # handles /students/*
app.include_router(explain_router)
app.include_router(notes_router)
app.include_router(quiz_router)
app.include_router(evaluate_router)
app.include_router(analytics_router)
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