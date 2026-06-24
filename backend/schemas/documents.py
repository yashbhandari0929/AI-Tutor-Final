from pydantic import BaseModel
from datetime import datetime


class UploadResponse(BaseModel):
    message: str
    document_id: int
    title: str
    chunk_count: int
    file_type: str = "pdf"


class DocumentOut(BaseModel):
    id: int
    title: str
    source: str
    uploaded_at: datetime
    chunk_count: int

    # ── Phase 8 additions ──────────────────────────────────────────────────
    file_type: str = "pdf"                 # "pdf" | "image"
    conversation_id: int | None = None     # None = global Knowledge Base doc

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int


class DeleteResponse(BaseModel):
    message: str
    document_id: int
