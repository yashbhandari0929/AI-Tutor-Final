from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.llm_service import generate_response
from database.database import SessionLocal
from auth.security import decode_access_token
from database.models import Note, StudentProfile, User
import re

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class NotesRequest(BaseModel):
    subject: str
    topic: str
    level: str
    length: str
    # student_id is optional so existing callers without it don't break
    student_id: int | None = None


def _resolve_student_id(
    db: Session,
    authorization: str | None,
    fallback_student_id: int | None,
) -> int | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id = int(payload.get("sub"))
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
                if student:
                    return student.id
        except Exception:
            pass
    return fallback_student_id


def markdown_to_html(text: str) -> str:
    """Convert markdown text to clean HTML for frontend rendering."""

    # Escape HTML special chars first (except we'll re-add our own tags)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = text.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        stripped = line.strip()

        # --- Headings ---
        if stripped.startswith("### "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = stripped[4:]
            content = apply_inline_styles(content)
            html_lines.append(f'<h3 class="notes-h3">{content}</h3>')

        elif stripped.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = stripped[3:]
            content = apply_inline_styles(content)
            html_lines.append(f'<h2 class="notes-h2">{content}</h2>')

        elif stripped.startswith("# "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = stripped[2:]
            content = apply_inline_styles(content)
            html_lines.append(f'<h1 class="notes-h1">{content}</h1>')

        # --- Horizontal rule ---
        elif stripped in ("---", "***", "___"):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append('<hr class="notes-hr" />')

        # --- Bullet points (*, -, +) ---
        elif re.match(r"^[\*\-\+]\s+", stripped):
            content = re.sub(r"^[\*\-\+]\s+", "", stripped)
            content = apply_inline_styles(content)
            if not in_ul:
                html_lines.append('<ul class="notes-ul">')
                in_ul = True
            html_lines.append(f'  <li class="notes-li">{content}</li>')

        # --- Numbered list ---
        elif re.match(r"^\d+\.\s+", stripped):
            content = re.sub(r"^\d+\.\s+", "", stripped)
            content = apply_inline_styles(content)
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<p class="notes-numbered">• {content}</p>')

        # --- Empty line ---
        elif stripped == "":
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("")

        # --- Normal paragraph ---
        else:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = apply_inline_styles(stripped)
            html_lines.append(f'<p class="notes-p">{content}</p>')

    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def apply_inline_styles(text: str) -> str:
    """Apply inline markdown: bold, italic, inline code."""

    # Bold+Italic: ***text***
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)

    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong class="notes-bold">\1</strong>', text)

    # Italic: *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)

    # Inline code: `code`
    text = re.sub(r"`(.+?)`", r'<code class="notes-code">\1</code>', text)

    return text


@router.post("/notes/generate")
def generate_notes(
    data: NotesRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):

    try:
        prompt = f"""
Create structured study notes.

Subject: {data.subject}
Topic: {data.topic}
Level: {data.level}
Length: {data.length}

Format:
- Introduction
- Key Concepts
- Examples
- Important Points
- Exam Tips
- Summary
"""

        notes = generate_response(prompt)

        if not notes:
            return {"notes": "No response from model. Try again.", "format": "text"}

        # Clean code fences
        notes = notes.replace("```", "").strip()

        # Convert markdown → HTML
        notes_html = markdown_to_html(notes)

        # ── Persist the topic to the notes table ──────────────────────────────
        # Only save if a logged-in student made this request
        resolved_student_id = _resolve_student_id(db, authorization, data.student_id)
        if resolved_student_id is not None:
            try:
                note_row = Note(
                    student_id=resolved_student_id,
                    subject=data.subject,
                    topic=data.topic,
                    level=data.level,
                )
                db.add(note_row)
                db.commit()
            except Exception as db_err:
                # Non-fatal: log and continue — don't fail the notes response
                print("WARNING: could not save note record to DB:", db_err)
                db.rollback()

        return {
            "notes": notes_html,
            "format": "html",       # ← tells frontend to use innerHTML / dangerouslySetInnerHTML
        }

    except Exception as e:
        print("ERROR in notes API:", e)

        return {
            "notes": "Server error while generating notes. Please try again.",
            "format": "text",
        }
