"""
api/documents.py

Endpoints:
  POST   /documents/upload      — upload a PDF, chunk + embed it
  GET    /documents             — list the current student's documents
  DELETE /documents/{id}        — delete a document and rebuild FAISS index

All endpoints are JWT-protected. student_id is NEVER accepted from the
frontend — it is always derived from the JWT via get_current_user.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import User, StudentProfile, Document, Conversation
from auth.dependencies import get_current_user
from schemas.documents import (
    UploadResponse,
    DocumentOut,
    DocumentListResponse,
    DeleteResponse,
)
from services.rag_service import ingest_pdf, store_image, delete_document_and_rebuild

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)

# ── Allowed MIME types ────────────────────────────────────────────────────────
_ALLOWED_PDF_TYPES = {"application/pdf"}
_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
_ALLOWED_CONTENT_TYPES = _ALLOWED_PDF_TYPES | _ALLOWED_IMAGE_TYPES
_MAX_FILE_SIZE_MB = 20
_MAX_FILE_SIZE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_student_or_404(user: User, db: Session) -> StudentProfile:
    """
    Resolve the StudentProfile for the authenticated user.
    Raises 404 if the profile is missing (shouldn't happen under normal
    registration flow, but guarded defensively).
    """
    student = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user.id)
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for this account.",
        )
    return student


# ── POST /documents/upload ────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF or image study attachment.

    - PDFs: validated, chunked, embedded, stored in FAISS + DB (unchanged
      behaviour from before Phase 8).
    - Images (Phase 8): validated and stored for preview/display only —
      not chunked/embedded (no vision step yet).
    - conversation_id (Phase 8, optional): when provided, this file is
      scoped to that one chat's attachment list ("+" upload in the new
      Chat page) instead of the student's global Knowledge Base. The
      conversation must belong to the calling student.
    - student_id is always derived from JWT — never supplied by the client.
    """
    # ── Validate content type ─────────────────────────────────────────────────
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only PDF or image (png/jpg/webp) files are supported. Received: {file.content_type}",
        )

    # ── Read file bytes ───────────────────────────────────────────────────────
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {_MAX_FILE_SIZE_MB} MB limit.",
        )

    # ── Resolve student ───────────────────────────────────────────────────────
    student = _get_student_or_404(current_user, db)

    # ── If scoped to a conversation, verify ownership ─────────────────────────
    if conversation_id is not None:
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not convo or convo.student_id != student.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

    filename = os.path.basename(file.filename or "uploaded_file")
    is_image = file.content_type in _ALLOWED_IMAGE_TYPES
    file_type = "image" if is_image else "pdf"

    # ── Ingest ────────────────────────────────────────────────────────────────
    try:
        logger.info(
            "Processing %s upload filename=%s size=%s student_id=%s conversation_id=%s",
            file_type,
            filename,
            len(file_bytes),
            student.id,
            conversation_id,
        )
        if is_image:
            result = store_image(
                file_bytes=file_bytes,
                filename=filename,
                student_id=student.id,
                db=db,
                conversation_id=conversation_id,
            )
        else:
            result = ingest_pdf(
                file_bytes=file_bytes,
                filename=filename,
                student_id=student.id,
                db=db,
                conversation_id=conversation_id,
            )
    except ValueError as exc:
        db.rollback()
        logger.warning("Document upload rejected filename=%s student_id=%s: %s", filename, student.id, exc)
        # ingest_pdf raises ValueError for unreadable/image-only PDFs
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception:
        db.rollback()
        logger.exception("Document upload failed filename=%s student_id=%s", filename, student.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document. Check server logs for the exact failure.",
        )

    return UploadResponse(
        message="File uploaded successfully." if is_image else "Document uploaded and indexed successfully.",
        document_id=result["document_id"],
        title=filename,
        chunk_count=result["chunk_count"],
        file_type=file_type,
    )


# ── GET /documents ────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=DocumentListResponse,
)
def list_documents(
    conversation_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List documents uploaded by the authenticated student.

    - No query param → all of the student's documents (old Knowledge Base
      behaviour, unchanged).
    - ?conversation_id=N (Phase 8) → only files attached to that one chat,
      for rendering the chat's own attachment sidebar.
    Each item includes chunk_count so the frontend can show indexing stats.
    """
    student = _get_student_or_404(current_user, db)

    query = db.query(Document).filter(Document.student_id == student.id)
    if conversation_id is not None:
        query = query.filter(Document.conversation_id == conversation_id)

    documents = query.order_by(Document.uploaded_at.desc()).all()

    doc_out = []
    for doc in documents:
        doc_out.append(
            DocumentOut(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                uploaded_at=doc.uploaded_at,
                chunk_count=len(doc.chunks),
                file_type=doc.file_type,
                conversation_id=doc.conversation_id,
            )
        )

    return DocumentListResponse(
        documents=doc_out,
        total=len(doc_out),
    )


# ── GET /documents/{id}/file ──────────────────────────────────────────────────

@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Serve the original uploaded bytes (PDF or image) for preview/download.
    Used by the Chat page to show a thumbnail/link in the attachments panel.
    """
    student = _get_student_or_404(current_user, db)

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.student_id != student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your document.")
    if not document.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file is not available for this document (uploaded before Phase 8).",
        )
    if not os.path.exists(document.file_path):
        logger.error("Missing uploaded file document_id=%s path=%s", document.id, document.file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original uploaded file is missing from storage.",
        )

    return FileResponse(document.file_path, filename=document.title)


# ── DELETE /documents/{id} ────────────────────────────────────────────────────

@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a document and all its chunks.
    Rebuilds the FAISS index after deletion to remove stale vectors.

    Returns 404 if the document doesn't exist.
    Returns 403 if the document belongs to a different student.
    """
    student = _get_student_or_404(current_user, db)

    # Ownership check happens inside delete_document_and_rebuild
    # which returns False for both "not found" and "wrong owner" cases.
    # We distinguish them here for better error messages.
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    if document.student_id != student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this document.",
        )

    success = delete_document_and_rebuild(
        document_id=document_id,
        student_id=student.id,
        db=db,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document. Please try again.",
        )

    return DeleteResponse(
        message="Document deleted and index rebuilt successfully.",
        document_id=document_id,
    )
