"""
api/conversations.py — Phase 8: ChatGPT-style saved chat history.

Endpoints:
  POST   /conversations                  — create a new (empty) chat
  GET    /conversations                  — list the student's chats (most recent first)
  GET    /conversations/{id}             — get one chat + its messages + attachments
  PATCH  /conversations/{id}             — rename a chat
  DELETE /conversations/{id}             — delete a chat (cascades messages; attached
                                            Documents are NOT deleted, just detached —
                                            see note in delete_conversation)
  POST   /conversations/{id}/messages    — send a message, get back the saved user
                                            + assistant message pair

This sits alongside the old POST /chat (api/chat.py), which keeps working
unmodified for backward compatibility. The new Chat page should call these
endpoints instead so messages are actually saved.

RAG scoping: a message in conversation N can "see" — for retrieval —
documents attached to conversation N, PLUS the student's global Knowledge
Base documents (conversation_id IS NULL). Documents attached to OTHER
conversations are never visible here.
"""

import base64
import mimetypes
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import User, StudentProfile, Conversation, Message, Document
from auth.dependencies import get_current_user
from services.llm_service import generate_response
from services.rag_service import (
    fallback_context_for_documents,
    retrieve_context_with_sources,
)
from services.text_format import SIMPLE_TUTOR_FORMAT, build_plain_prompt, normalize_legacy_answer
from schemas.chat import (
    ConversationOut,
    ConversationListResponse,
    ConversationDetail,
    MessageOut,
    CreateMessageRequest,
    SendMessageResponse,
    RenameConversationRequest,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_student_or_404(user: User, db: Session) -> StudentProfile:
    student = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user.id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found for this account.")
    return student


def _get_owned_conversation_or_404(conversation_id: int, student_id: int, db: Session) -> Conversation:
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if convo.student_id != student_id:
        raise HTTPException(status_code=403, detail="Not your conversation.")
    return convo


def _is_attachment_question(message: str) -> bool:
    lowered = message.lower()
    signals = (
        "attached",
        "attachment",
        "above",
        "file",
        "document",
        "pdf",
        "image",
        "photo",
        "certificate",
        "written",
        "summarize",
        "summary",
        "issued",
        "issuer",
        "course",
        "read",
        "explain the attached",
    )
    return any(signal in lowered for signal in signals)


def _build_history(messages: list[Message], max_messages: int = 12) -> str:
    prior_messages = messages[-max_messages:]
    lines = []
    for msg in prior_messages:
        role = "User" if msg.role == "user" else "Assistant"
        content = msg.content if msg.role == "user" else normalize_legacy_answer(msg.content)
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "No previous conversation."


def _build_file_aware_prompt(
    message: str,
    history: str,
    context_chunks: list,
    image_sources: list[str],
) -> str:
    if context_chunks:
        context_text = "\n\n---\n\n".join(
            f"Source: {chunk.source}\n{chunk.text}" for chunk in context_chunks
        )
    elif image_sources:
        context_text = (
            "The current conversation has attached image files that are being sent "
            "with this message for visual understanding:\n"
            + "\n".join(f"- {source}" for source in image_sources)
        )
    else:
        context_text = "No relevant attached-file context was found."

    return f"""You are an expert AI tutor with access to this conversation's attached files.

{SIMPLE_TUTOR_FORMAT}

Use the conversation history for continuity. Use attached-file context as the primary source when it is relevant.
If the user asks about an attached file, answer from the attached file context without requiring them to say "use the file".
If the attached context is insufficient, say what is missing and answer only what can be supported.
Never paste attached-file chunks verbatim. Turn them into a plain, spoken-style explanation.

CONVERSATION HISTORY:
{history}

CONTEXT FROM ATTACHED FILES:
{context_text}

USER QUESTION:
{message}

Answer clearly and directly in plain prose, the way a tutor would say it out loud. When the answer comes from
attached files, mention the relevant file name naturally in a sentence.
"""


# ── POST /conversations ──────────────────────────────────────────────────────

@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new empty chat. Title defaults to 'New Chat' until the first message."""
    student = _get_student_or_404(current_user, db)
    convo = Conversation(student_id=student.id)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


# ── GET /conversations ───────────────────────────────────────────────────────

@router.get("", response_model=ConversationListResponse)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the student's chats, most recently active first."""
    student = _get_student_or_404(current_user, db)
    convos = (
        db.query(Conversation)
        .filter(Conversation.student_id == student.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return ConversationListResponse(conversations=convos)


# ── GET /conversations/{id} ──────────────────────────────────────────────────

@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one chat's full message history + attached files."""
    student = _get_student_or_404(current_user, db)
    convo = _get_owned_conversation_or_404(conversation_id, student.id, db)

    attachments = [
        {
            "id": doc.id,
            "title": doc.title,
            "file_type": doc.file_type,
            "chunk_count": len(doc.chunks),
            "uploaded_at": doc.uploaded_at.isoformat(),
        }
        for doc in convo.attachments
    ]

    return ConversationDetail(
        id=convo.id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        messages=convo.messages,
        attachments=attachments,
    )


# ── PATCH /conversations/{id} ────────────────────────────────────────────────

@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: int,
    data: RenameConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _get_student_or_404(current_user, db)
    convo = _get_owned_conversation_or_404(conversation_id, student.id, db)
    convo.title = data.title.strip() or convo.title
    convo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(convo)
    return convo


# ── DELETE /conversations/{id} ───────────────────────────────────────────────

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a chat and its messages.

    Files attached to this chat are NOT deleted — they're detached
    (conversation_id set back to NULL), so they fall back into the
    student's global Knowledge Base instead of disappearing. Change this
    to actually delete + rebuild FAISS if you'd rather attachments die
    with the chat — ask if you want that behavior instead.
    """
    student = _get_student_or_404(current_user, db)
    convo = _get_owned_conversation_or_404(conversation_id, student.id, db)

    db.query(Document).filter(Document.conversation_id == convo.id).update(
        {"conversation_id": None}
    )
    db.delete(convo)
    db.commit()
    return {"message": "Conversation deleted.", "conversation_id": conversation_id}


# ── POST /conversations/{id}/messages ────────────────────────────────────────

@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: int,
    data: CreateMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message in an existing chat. Saves the user message, runs the
    same RAG-or-plain Gemini flow as the legacy /chat endpoint (scoped to
    this chat's attachments + the global Knowledge Base), saves the
    assistant's reply, and returns both.
    """
    student = _get_student_or_404(current_user, db)
    convo = _get_owned_conversation_or_404(conversation_id, student.id, db)

    # ── Save the user's message first ────────────────────────────────────────
    user_msg = Message(conversation_id=convo.id, role="user", content=data.message)
    db.add(user_msg)

    # Auto-title a fresh chat from its first message.
    if convo.title == "New Chat":
        convo.title = data.message.strip()[:60] or "New Chat"

    db.flush()  # assign user_msg.id without committing yet

    attached_docs = (
        db.query(Document)
        .filter(
            Document.student_id == student.id,
            Document.conversation_id == convo.id,
        )
        .all()
    )

    attached_doc_ids = [doc.id for doc in attached_docs]
    image_docs = [doc for doc in attached_docs if doc.file_type == "image" and doc.file_path]

    context_chunks = []
    if attached_doc_ids:
        try:
            context_chunks = retrieve_context_with_sources(
                query=data.message,
                student_id=student.id,
                db=db,
                document_ids=attached_doc_ids,
            )
            if not context_chunks and _is_attachment_question(data.message):
                context_chunks = fallback_context_for_documents(
                    db=db,
                    student_id=student.id,
                    document_ids=attached_doc_ids,
                    limit=max(5, min(12, len(attached_doc_ids) * 3)),
                )
        except Exception as exc:
            print(f"[conversations] Attached-file retrieval failed, falling back: {exc}")
            context_chunks = []

    image_parts: list[dict] = []
    image_sources: list[str] = []
    for img_doc in image_docs:
        try:
            with open(img_doc.file_path, "rb") as fh:
                img_bytes = fh.read()
            mime = mimetypes.guess_type(img_doc.file_path)[0] or "image/png"
            image_parts.append({
                "mime_type": mime,
                "data": base64.b64encode(img_bytes).decode("utf-8"),
                "title": img_doc.title,
            })
            image_sources.append(img_doc.title)
        except Exception as exc:
            print(f"[conversations] Could not read image {img_doc.id}: {exc}")

    history_messages = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id, Message.id != user_msg.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = _build_history(history_messages)

    used_file_context = bool(context_chunks or image_parts)
    if used_file_context:
        prompt = _build_file_aware_prompt(
            message=data.message,
            history=history,
            context_chunks=context_chunks,
            image_sources=image_sources,
        )
    else:
        prompt = f"""Conversation History:
{history}

Current User Message:
{data.message}

{build_plain_prompt(data.message)}
"""

    response = generate_response(prompt, image_parts=image_parts if image_parts else None)
    reply_markdown = normalize_legacy_answer(response) if response else "No response. Try again."

    sources = []
    for chunk in context_chunks:
        if chunk.source not in sources:
            sources.append(chunk.source)
    for source in image_sources:
        if source not in sources:
            sources.append(source)

    assistant_msg = Message(
        conversation_id=convo.id,
        role="assistant",
        content=reply_markdown,
        used_rag=used_file_context,
    )
    db.add(assistant_msg)

    convo.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return SendMessageResponse(
        user_message={
            "id": user_msg.id,
            "role": user_msg.role,
            "content": user_msg.content,
            "used_rag": bool(user_msg.used_rag),
            "used_file_context": False,
            "sources": [],
            "created_at": user_msg.created_at,
        },
        assistant_message={
            "id": assistant_msg.id,
            "role": assistant_msg.role,
            "content": assistant_msg.content,
            "used_rag": bool(assistant_msg.used_rag),
            "used_file_context": used_file_context,
            "sources": sources,
            "created_at": assistant_msg.created_at,
        },
        used_file_context=used_file_context,
        sources=sources,
    )