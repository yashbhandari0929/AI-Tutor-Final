from __future__ import annotations

import io
import json
import re
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from database.models import InterviewAnswer, InterviewQuestion, InterviewSession
from services.llm_service import generate_response


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _dump(value: list[str]) -> str:
    return json.dumps(value or [])


def _extract_json_object(text: str | None) -> dict:
    if not text:
        return {}
    cleaned = text.replace("```json", "```").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _extract_json_array(text: str | None) -> list:
    if not text:
        return []
    cleaned = text.replace("```json", "```").replace("```", "").strip()
    match = re.search(r"\[.*\]", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as exc:
        raise ValueError(f"Could not parse PDF text: {exc}") from exc


def _fallback_resume_analysis(text: str) -> dict:
    skill_keywords = [
        "python", "java", "javascript", "typescript", "react", "next.js",
        "sql", "fastapi", "django", "node", "machine learning", "ai",
        "data analysis", "aws", "azure", "docker", "git",
    ]
    lowered = text.lower()
    skills = [skill for skill in skill_keywords if skill in lowered]
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    projects = [line for line in lines if "project" in line.lower()][:5]
    education = [line for line in lines if any(word in line.lower() for word in ("degree", "university", "college", "b.tech", "bachelor", "master"))][:5]
    experience = [line for line in lines if any(word in line.lower() for word in ("intern", "experience", "developer", "engineer", "worked"))][:5]
    score = min(85, 35 + len(skills) * 5 + len(projects) * 5 + len(experience) * 4)
    gaps = ["System design", "Database fundamentals", "Project deep-dives"] if skills else ["Add clearer technical skills"]
    return {
        "name": "",
        "resume_score": score,
        "ats_score": max(30, score - 5),
        "skills": skills[:12],
        "projects": projects,
        "experience": experience,
        "education": education,
        "skill_gap_analysis": gaps,
        "strengths": ["Resume parsed successfully", "Use project examples in answers"],
        "improvements": ["Quantify impact", "Add role-specific keywords"],
    }


def analyze_resume(file_bytes: bytes, filename: str, student_id: int, db: Session) -> InterviewSession:
    text = extract_pdf_text(file_bytes)
    prompt = f"""
Analyze this resume for interview preparation.
Return ONLY JSON with keys:
name, resume_score, ats_score, skills, projects, experience, education,
skill_gap_analysis, strengths, improvements.
Scores must be 0-100. Arrays must contain short strings.

RESUME:
{text[:12000]}
"""
    parsed = _extract_json_object(generate_response(prompt))
    if not parsed:
        parsed = _fallback_resume_analysis(text)

    session = InterviewSession(
        student_id=student_id,
        resume_name=filename,
        resume_text=text,
        name=str(parsed.get("name") or ""),
        resume_score=float(parsed.get("resume_score") or 0),
        ats_score=float(parsed.get("ats_score") or 0),
        skills=_dump(parsed.get("skills") or []),
        projects=_dump(parsed.get("projects") or []),
        experience=_dump(parsed.get("experience") or []),
        education=_dump(parsed.get("education") or []),
        skill_gap_analysis=_dump(parsed.get("skill_gap_analysis") or []),
        strengths=_dump(parsed.get("strengths") or []),
        improvements=_dump(parsed.get("improvements") or []),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def session_to_analysis(session: InterviewSession) -> dict:
    return {
        "session_id": session.id,
        "resume_name": session.resume_name,
        "name": session.name,
        "resume_score": session.resume_score,
        "ats_score": session.ats_score,
        "skills": _json_list(session.skills),
        "projects": _json_list(session.projects),
        "experience": _json_list(session.experience),
        "education": _json_list(session.education),
        "skill_gap_analysis": _json_list(session.skill_gap_analysis),
        "strengths": _json_list(session.strengths),
        "improvements": _json_list(session.improvements),
    }


def generate_questions(session: InterviewSession, difficulty: str, db: Session) -> list[InterviewQuestion]:
    prompt = f"""
Generate interview questions from this resume.
Difficulty: {difficulty}
Return ONLY a JSON array of 12 objects:
question, category, difficulty.
Include Technical, Behavioral, HR, Project-Based, and Resume-Specific questions.

SKILLS: {session.skills}
PROJECTS: {session.projects}
EXPERIENCE: {session.experience}
RESUME TEXT:
{(session.resume_text or '')[:8000]}
"""
    parsed = _extract_json_array(generate_response(prompt))
    if not parsed:
        skills = _json_list(session.skills) or ["the candidate's strongest listed skill"]
        projects = _json_list(session.projects) or ["a resume project"]
        parsed = [
            {"question": f"Explain your experience with {skills[0]}.", "category": "Technical", "difficulty": difficulty},
            {"question": f"Walk me through {projects[0]} and your contribution.", "category": "Project-Based", "difficulty": difficulty},
            {"question": "Tell me about a challenge you faced and how you handled it.", "category": "Behavioral", "difficulty": difficulty},
            {"question": "Why are you interested in this role?", "category": "HR", "difficulty": difficulty},
        ]

    rows: list[InterviewQuestion] = []
    for item in parsed[:15]:
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        rows.append(InterviewQuestion(
            session_id=session.id,
            question=question,
            category=str(item.get("category") or "Technical"),
            difficulty=str(item.get("difficulty") or difficulty),
        ))
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def question_to_dict(question: InterviewQuestion, answered_ids: set[int] | None = None) -> dict:
    return {
        "id": question.id,
        "question": question.question,
        "category": question.category,
        "difficulty": question.difficulty,
        "answered": question.id in (answered_ids or set()),
    }


def evaluate_answer(
    session: InterviewSession,
    question: str,
    answer: str,
    db: Session,
    question_id: int | None = None,
) -> dict:
    prompt = f"""
Evaluate this mock interview answer.
Return ONLY JSON with keys:
score, feedback, strengths, weaknesses, suggested_improvement.

Resume skills: {session.skills}
Question: {question}
Answer: {answer}
"""
    parsed = _extract_json_object(generate_response(prompt))
    if not parsed:
        parsed = {
            "score": 55 if len(answer.split()) >= 25 else 35,
            "feedback": "Answer recorded. Add clearer structure, evidence, and measurable impact.",
            "strengths": ["Directly attempted the question"],
            "weaknesses": ["Needs more specific examples", "Could be structured more clearly"],
            "suggested_improvement": "Use Situation, Task, Action, Result, then connect the result to the role.",
        }

    row = InterviewAnswer(
        session_id=session.id,
        question_id=question_id,
        answer=answer,
        feedback=str(parsed.get("feedback") or ""),
        strengths=_dump(parsed.get("strengths") or []),
        weaknesses=_dump(parsed.get("weaknesses") or []),
        suggested_improvement=str(parsed.get("suggested_improvement") or ""),
        score=float(parsed.get("score") or 0),
    )
    db.add(row)
    db.flush()
    _refresh_session_report(session, db)
    db.commit()
    db.refresh(row)
    return {
        "score": row.score,
        "feedback": row.feedback,
        "strengths": _json_list(row.strengths),
        "weaknesses": _json_list(row.weaknesses),
        "suggested_improvement": row.suggested_improvement,
        "answer_id": row.id,
    }


def _refresh_session_report(session: InterviewSession, db: Session) -> None:
    answers = db.query(InterviewAnswer).filter(InterviewAnswer.session_id == session.id).all()
    if not answers:
        session.readiness_score = session.resume_score or 0
        return
    avg_score = sum(answer.score or 0 for answer in answers) / len(answers)
    weakness_counter: Counter[str] = Counter()
    for answer in answers:
        weakness_counter.update(_json_list(answer.weaknesses))
    weak_areas = [area for area, _ in weakness_counter.most_common(8)]
    skill_gaps = _json_list(session.skill_gap_analysis)
    session.readiness_score = round((avg_score * 0.7) + ((session.resume_score or 0) * 0.3), 1)
    session.weak_skill_areas = _dump(weak_areas or skill_gaps)
    session.recommended_topics = _dump((weak_areas or skill_gaps or _json_list(session.skills))[:8])


def session_report(session: InterviewSession) -> dict:
    answers = session.answers
    avg_answer_score = round(sum(a.score or 0 for a in answers) / len(answers), 1) if answers else 0
    answered_ids = {a.question_id for a in answers if a.question_id}
    return {
        "id": session.id,
        "resume_name": session.resume_name,
        "resume_score": session.resume_score,
        "ats_score": session.ats_score,
        "readiness_score": session.readiness_score or session.resume_score or 0,
        "weak_skill_areas": _json_list(session.weak_skill_areas) or _json_list(session.skill_gap_analysis),
        "recommended_topics": _json_list(session.recommended_topics) or _json_list(session.skill_gap_analysis),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "question_count": len(session.questions),
        "answer_count": len(answers),
        "average_answer_score": avg_answer_score,
        "questions": [question_to_dict(q, answered_ids) for q in session.questions],
        "answers": [
            {
                "id": answer.id,
                "question_id": answer.question_id,
                "answer": answer.answer,
                "feedback": answer.feedback,
                "strengths": _json_list(answer.strengths),
                "weaknesses": _json_list(answer.weaknesses),
                "suggested_improvement": answer.suggested_improvement,
                "score": answer.score,
            }
            for answer in answers
        ],
    }


def interview_analytics(sessions: list[InterviewSession]) -> dict:
    reports = [session_report(session) for session in sessions]
    scores = [report["readiness_score"] for report in reports if report["readiness_score"]]
    weak_counter: Counter[str] = Counter()
    category_scores: dict[str, list[float]] = defaultdict(list)
    skill_scores: dict[str, list[float]] = defaultdict(list)

    for session in sessions:
        for area in _json_list(session.weak_skill_areas) or _json_list(session.skill_gap_analysis):
            weak_counter[area] += 1
        for answer in session.answers:
            if answer.question:
                category_scores[answer.question.category].append(answer.score or 0)
            for skill in _json_list(session.skills)[:8]:
                skill_scores[skill].append(answer.score or 0)

    return {
        "average_interview_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "best_interview_score": max(scores) if scores else 0,
        "total_interviews": len(sessions),
        "most_common_weak_areas": [
            {"area": area, "count": count} for area, count in weak_counter.most_common(8)
        ],
        "skill_radar": [
            {"skill": skill, "score": round(sum(values) / len(values), 1)}
            for skill, values in list(skill_scores.items())[:8]
        ],
        "question_categories_performance": [
            {"category": category, "average_score": round(sum(values) / len(values), 1), "attempts": len(values)}
            for category, values in category_scores.items()
        ],
    }
