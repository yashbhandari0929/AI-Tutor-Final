"""
services/rag_service.py

Orchestrates the full RAG pipeline:
  1. Embedding model — loaded ONCE at module import, reused forever.
  2. PDF ingestion   — extract text → chunk → embed → store in FAISS + DB.
  3. Retrieval       — embed query → FAISS search → filter by student → return chunks.

Dependencies:
    pip install sentence-transformers pypdf langchain langchain-community faiss-cpu
    pip install pymupdf pytesseract pillow   # for the Devanagari OCR fallback below

System dependency (for OCR fallback only):
    Tesseract OCR binary + language data for the scripts you care about, e.g.:
        Ubuntu/Debian: apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san tesseract-ocr-mar
    Without "hin"/"san"/"mar" tessdata installed, OCR fallback for Devanagari
    text will not work (Tesseract only has "eng" by default) and ingestion will
    log a warning and keep the (possibly garbled) text-layer extraction instead
    of silently producing empty/wrong results.
"""

from __future__ import annotations

import io
import os
import re
import uuid
from dataclasses import dataclass
import numpy as np

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from database.models import Document, DocumentChunk
from rag.faiss_store import add_embeddings, search, rebuild

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

try:
    import fitz  # PyMuPDF — used to rasterize PDF pages for OCR fallback
except Exception:
    fitz = None

# ── Original-file storage (Phase 8) ───────────────────────────────────────────
# Original bytes are saved to disk so the frontend can preview/download the
# exact uploaded file later (GET /documents/{id}/file). Previously only the
# extracted text was kept — the raw PDF/image itself was discarded after
# ingestion, which is fine for RAG but not for "show it in the sidebar".
_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploaded_files")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


def _save_to_disk(file_bytes: bytes, student_id: int, filename: str) -> str:
    """Save raw bytes under uploaded_files/<student_id>/<filename>, return the path."""
    student_dir = os.path.join(_UPLOAD_DIR, str(student_id))
    os.makedirs(student_dir, exist_ok=True)
    # Prefix with a short random token to avoid collisions on repeat filenames.
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    path = os.path.join(student_dir, safe_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path

# ── Embedding model singleton ─────────────────────────────────────────────────
# Loaded once when this module is first imported (at server startup).
# all-MiniLM-L6-v2 is ~80 MB, runs on CPU, produces 384-dim vectors.
# Re-using this instance across requests avoids the ~2-3 second reload cost.
print("[rag_service] Loading SentenceTransformer model…")
_EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
print("[rag_service] SentenceTransformer ready.")

# ── Chunking config ───────────────────────────────────────────────────────────
# 500 chars ≈ ~120 tokens for typical English study text.
# 50-char overlap preserves sentence continuity across chunk boundaries.
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],
)

# Similarity threshold — L2 distance above this means "not relevant".
# Tune upward if you see too many irrelevant results; downward if
# relevant chunks are being filtered out.
# L2 distance for 384-dim MiniLM: ~0 = identical, ~1.5+ = unrelated.
DISTANCE_THRESHOLD = 1.2

# How many FAISS neighbours to fetch before student-scoping filter
_FAISS_FETCH_K = 20

# How many chunks to inject into the prompt after filtering
TOP_K_CONTEXT = 5


@dataclass
class RetrievedContext:
    text: str
    source: str
    document_id: int
    file_type: str
    distance: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _embed(texts: list[str]) -> np.ndarray:
    """
    Embed a list of strings. Returns float32 ndarray of shape (n, 384).
    batch_size=32 is fine for study-material volumes.
    """
    return _EMBEDDER.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False,   # FlatL2 doesn't need normalisation
    ).astype(np.float32)


_OCR_LANGS = "hin+san+mar"  # Hindi + Sanskrit + Marathi tessdata, all Devanagari script
_OCR_DPI = 300              # good balance of OCR accuracy vs. speed for text pages

# Devanagari Unicode block: U+0900–U+097F.
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# A "dangling combining mark" is a vowel sign (matra) or virama that appears
# with no Devanagari base consonant/vowel immediately before it. This is the
# signature pattern left behind when a PDF's font has a broken/partial
# ToUnicode CMap for conjunct glyphs: pypdf reads the matra/virama glyph
# correctly but drops the consonant it was supposed to attach to, e.g.
# "नमस्ते" (correct) extracting as "नमे" (मस्त् silently lost).
# U+093E–U+094D covers the dependent vowel signs, virama, and similar marks.
_DANGLING_MARK_RE = re.compile(
    r"(?:^|[^\u0900-\u097F])[\u093E-\u094D]"
)


def _looks_like_garbled_devanagari(text: str) -> bool:
    """
    Heuristic check: does this text contain enough Devanagari to matter, and
    does it show the "dangling combining mark" pattern typical of a PDF whose
    embedded font has a broken CMap for conjunct consonants?

    This is intentionally a coarse trigger, not a precision classifier — it's
    only used to decide whether a page is worth the cost of OCR fallback, and
    false positives just mean we OCR a page that was already fine (wasted
    time, not wrong data). False negatives (missing a garbled page) are the
    real risk, so the threshold below is kept low on purpose.
    """
    devanagari_chars = _DEVANAGARI_RE.findall(text)
    if len(devanagari_chars) < 20:
        # Not enough Devanagari content on this page for the check to be
        # meaningful either way (e.g. mostly-English page with a stray word).
        return False

    dangling_hits = len(_DANGLING_MARK_RE.findall(text))
    # Real Devanagari prose has dangling marks approach zero. Anything more
    # than a small fraction of total Devanagari chars indicates systematic
    # conjunct loss rather than the occasional OCR/typo edge case.
    return dangling_hits / max(len(devanagari_chars), 1) > 0.03


def _ocr_pdf_page(doc: "fitz.Document", page_index: int) -> str:
    """
    Rasterize one PDF page to an image and OCR it with Tesseract, using
    Devanagari-capable language data. Returns "" on any failure so a single
    bad page never aborts the whole ingestion.
    """
    if pytesseract is None or Image is None:
        print("[rag_service] OCR fallback skipped: pytesseract/Pillow not installed.")
        return ""

    try:
        page = doc[page_index]
        zoom = _OCR_DPI / 72  # PDF default is 72 DPI; scale up for OCR accuracy
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(image, lang=_OCR_LANGS)
        return (text or "").strip()
    except pytesseract.TesseractError as exc:
        # Most common cause: hin/san/mar tessdata not installed on this server.
        print(
            f"[rag_service] OCR fallback failed on page {page_index + 1} "
            f"(is '{_OCR_LANGS}' tessdata installed?): {exc}"
        )
        return ""
    except Exception as exc:
        print(f"[rag_service] OCR fallback failed on page {page_index + 1}: {exc}")
        return ""


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF given its raw bytes.
    Returns a single string with pages separated by newlines.
    Raises ValueError if no text could be extracted (e.g. scanned image PDF).

    Devanagari fallback: pypdf reads text strictly through each PDF's
    embedded ToUnicode CMap. Some Devanagari/Sanskrit PDFs ship fonts with
    broken or partial CMaps for conjunct glyphs, which makes pypdf silently
    drop consonants (e.g. "नमस्ते" → "नमे"). When a page's text-layer
    extraction looks garbled in that specific way, that page is re-rendered
    as an image and re-extracted via OCR (Tesseract, hin+san+mar) instead.
    Pages that extract cleanly are left untouched — OCR is slower and only
    used where the text layer is actually broken.
    """
    reader = PdfReader(io.BytesIO(file_bytes))

    # Only open with PyMuPDF if we might need to rasterize a page — avoids
    # the extra dependency/cost entirely for documents with clean text layers.
    fitz_doc = None

    try:
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()

            if text and _looks_like_garbled_devanagari(text):
                if fitz is None:
                    print(
                        "[rag_service] Page looks like garbled Devanagari but "
                        "PyMuPDF ('fitz') isn't installed — keeping text-layer "
                        "extraction as-is. Run: pip install pymupdf"
                    )
                else:
                    if fitz_doc is None:
                        fitz_doc = fitz.open(stream=file_bytes, filetype="pdf")
                    ocr_text = _ocr_pdf_page(fitz_doc, i)
                    if ocr_text:
                        print(f"[rag_service] Page {i + 1}: used OCR fallback for Devanagari text.")
                        text = ocr_text
                    else:
                        print(
                            f"[rag_service] Page {i + 1}: OCR fallback produced no text — "
                            "keeping original (possibly garbled) extraction."
                        )

            if text:
                pages.append(text)
    finally:
        if fitz_doc is not None:
            fitz_doc.close()

    if not pages:
        raise ValueError(
            "No extractable text found in this PDF. "
            "Scanned/image-only PDFs are not supported yet."
        )

    return "\n\n".join(pages)


def _extract_text_from_image(file_bytes: bytes) -> str:
    """
    OCR text from an image. Returns an empty string when OCR dependencies
    are unavailable or when no text is detected.
    """
    if pytesseract is None or Image is None:
        print("[rag_service] OCR skipped: pytesseract/Pillow is not installed.")
        return ""

    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        return (text or "").strip()
    except Exception as exc:
        print(f"[rag_service] OCR failed: {exc}")
        return ""


def _persist_chunks_for_document(
    db: Session,
    document: Document,
    chunks: list[str],
) -> None:
    if not chunks:
        return

    embeddings = _embed(chunks)
    chunk_rows = []

    for chunk_text in chunks:
        row = DocumentChunk(
            document_id=document.id,
            chunk_text=chunk_text,
            embedding_id=None,
        )
        db.add(row)
        chunk_rows.append(row)

    db.flush()

    chunk_ids = [row.id for row in chunk_rows]
    positions = add_embeddings(embeddings, chunk_ids)

    for row, pos in zip(chunk_rows, positions):
        row.embedding_id = pos


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_pdf(
    file_bytes: bytes,
    filename: str,
    student_id: int,
    db: Session,
    conversation_id: int | None = None,
) -> dict:
    """
    Full ingestion pipeline for an uploaded PDF.

    Steps:
      1. Extract text from PDF bytes.
      2. Split text into overlapping chunks.
      3. Embed all chunks in one batch.
      4. Persist Document + DocumentChunk rows (with embedding_id=None first).
      5. Add embeddings to FAISS, get back positions.
      6. Update each chunk's embedding_id with its FAISS position.
      7. Save the original PDF bytes to disk for later preview/download.
      8. Commit.

    conversation_id (Phase 8): if given, this upload is scoped to one chat's
    attachment list instead of the student's global Knowledge Base. Pass
    None to keep the original (global) behaviour.

    Returns { "document_id": int, "chunk_count": int }
    """
    # ── Step 1: extract text ──────────────────────────────────────────────────
    raw_text = _extract_text_from_pdf(file_bytes)

    # ── Step 2: chunk ─────────────────────────────────────────────────────────
    chunks = _SPLITTER.split_text(raw_text)
    if not chunks:
        raise ValueError("PDF produced no text chunks after splitting.")

    # ── Step 3: embed ─────────────────────────────────────────────────────────
    embeddings = _embed(chunks)          # shape: (len(chunks), 384)

    # ── Step 4: persist Document + chunks (embedding_id filled in step 6) ─────
    document = Document(
        student_id=student_id,
        conversation_id=conversation_id,
        title=filename,
        source="pdf_upload",
        file_type="pdf",
    )
    db.add(document)
    db.flush()          # assigns document.id without committing

    chunk_rows = []
    for chunk_text in chunks:
        row = DocumentChunk(
            document_id=document.id,
            chunk_text=chunk_text,
            embedding_id=None,          # filled after FAISS add
        )
        db.add(row)
        chunk_rows.append(row)

    db.flush()          # assigns each chunk row's .id

    # ── Step 5: add to FAISS ──────────────────────────────────────────────────
    chunk_ids  = [row.id for row in chunk_rows]
    positions  = add_embeddings(embeddings, chunk_ids)
    # positions[i] = FAISS row index for chunk_rows[i]

    # ── Step 6: write embedding_id back to each chunk ─────────────────────────
    for row, pos in zip(chunk_rows, positions):
        row.embedding_id = pos

    # ── Step 7: persist original bytes for preview/download ──────────────────
    document.file_path = _save_to_disk(file_bytes, student_id, filename)
    # NOTE: previously this also re-ran OCR on the raw PDF bytes as if they
    # were a plain image (wrong language pack — defaults to English-only,
    # and PIL can't even decode raw PDF bytes as an image in most cases)
    # and persisted a SECOND, duplicate, garbled batch of chunks on top of
    # the correct ones from _extract_text_from_pdf() above. That step has
    # been removed — _extract_text_from_pdf() already runs the proper
    # Devanagari-aware OCR fallback (hin+san+mar, page-rasterized via
    # PyMuPDF) only on the specific pages that actually need it.

    # ── Step 8: commit everything atomically ──────────────────────────────────
    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "chunk_count": len(chunk_rows),
    }


def store_image(
    file_bytes: bytes,
    filename: str,
    student_id: int,
    db: Session,
    conversation_id: int | None = None,
) -> dict:
    """
    Store an uploaded image (Phase 8) as a chat attachment.

    Images are NOT chunked/embedded — there's no text-extraction/vision
    step yet, so they're saved for display/preview only and don't feed
    the RAG pipeline. (Future enhancement: run them through a vision
    model and embed a caption/description so questions about a photo's
    content can be RAG-retrieved too — out of scope for this pass.)

    Returns { "document_id": int, "chunk_count": 0 }
    """
    document = Document(
        student_id=student_id,
        conversation_id=conversation_id,
        title=filename,
        source="image_upload",
        file_type="image",
    )
    db.add(document)
    db.flush()

    document.file_path = _save_to_disk(file_bytes, student_id, filename)

    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "chunk_count": 0,
    }


def retrieve_context(
    query: str,
    student_id: int,
    db: Session,
    document_ids: list[int] | None = None,
) -> list[str]:
    """
    Retrieve the top relevant text chunks for a query, scoped to one student.

    Parameters
    ----------
    document_ids : optional allow-list of Document.id values (Phase 8).
        When provided, only chunks belonging to one of these documents are
        considered — used by the conversation-scoped chat endpoint so a
        chat only "sees" the files attached to it (+ its student's global
        Knowledge Base docs, which the caller includes in this list).
        When None (legacy /chat endpoint), behaviour is unchanged — every
        document owned by the student is searchable.

    Steps:
      1. Embed the query.
      2. Search FAISS for the nearest _FAISS_FETCH_K neighbours.
      3. Load the matching DocumentChunk rows from DB.
      4. Filter: keep only chunks whose document belongs to student_id
         (and, if document_ids given, is in that allow-list).
      5. Filter: discard chunks whose L2 distance exceeds DISTANCE_THRESHOLD.
      6. Return up to TOP_K_CONTEXT chunk texts, closest-first.

    Returns an empty list if nothing relevant is found — callers should
    fall back to the plain LLM response in that case.
    """
    # ── Step 1: embed query ───────────────────────────────────────────────────
    query_vec = _embed([query])[0]      # shape: (384,)

    # ── Step 2: FAISS search ──────────────────────────────────────────────────
    raw_results = search(query_vec, top_k=_FAISS_FETCH_K)
    # raw_results: [{ "chunk_id": int, "distance": float }, ...]

    if not raw_results:
        return []

    # ── Step 3: load chunk rows ───────────────────────────────────────────────
    chunk_id_to_distance = {r["chunk_id"]: r["distance"] for r in raw_results}
    chunk_ids = list(chunk_id_to_distance.keys())

    chunk_rows = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )

    # ── Steps 4 & 5: student-scope (+ optional doc allow-list) + distance filter
    allow_set = set(document_ids) if document_ids is not None else None
    filtered = []
    for chunk in chunk_rows:
        # Security: never return another student's content
        if chunk.document.student_id != student_id:
            continue

        # Phase 8: conversation-scoped retrieval
        if allow_set is not None and chunk.document_id not in allow_set:
            continue

        dist = chunk_id_to_distance[chunk.id]
        if dist > DISTANCE_THRESHOLD:
            continue

        filtered.append((dist, chunk.chunk_text))

    if not filtered:
        return []

    # ── Step 6: sort by distance, return top K texts ──────────────────────────
    filtered.sort(key=lambda x: x[0])
    return [text for _, text in filtered[:TOP_K_CONTEXT]]


def retrieve_context_with_sources(
    query: str,
    student_id: int,
    db: Session,
    document_ids: list[int],
) -> list[RetrievedContext]:
    """Retrieve relevant chunks and include their source document metadata."""
    if not document_ids:
        return []

    query_vec = _embed([query])[0]
    raw_results = search(query_vec, top_k=_FAISS_FETCH_K)
    if not raw_results:
        return []

    chunk_id_to_distance = {r["chunk_id"]: r["distance"] for r in raw_results}
    chunk_ids = list(chunk_id_to_distance.keys())
    allow_set = set(document_ids)

    chunk_rows = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )

    filtered: list[RetrievedContext] = []
    for chunk in chunk_rows:
        if chunk.document.student_id != student_id:
            continue
        if chunk.document_id not in allow_set:
            continue

        dist = chunk_id_to_distance[chunk.id]
        if dist > DISTANCE_THRESHOLD:
            continue

        filtered.append(
            RetrievedContext(
                text=chunk.chunk_text,
                source=chunk.document.title,
                document_id=chunk.document_id,
                file_type=chunk.document.file_type,
                distance=dist,
            )
        )

    filtered.sort(key=lambda item: item.distance)
    return filtered[:TOP_K_CONTEXT]


def fallback_context_for_documents(
    db: Session,
    student_id: int,
    document_ids: list[int],
    limit: int = TOP_K_CONTEXT,
) -> list[RetrievedContext]:
    """
    Return the first available chunks from attached documents. Used only for
    broad attachment questions like "summarize this PDF" where semantic search
    can be too generic to clear the distance threshold.
    """
    if not document_ids:
        return []

    rows = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.student_id == student_id,
            DocumentChunk.document_id.in_(document_ids),
        )
        .order_by(DocumentChunk.document_id.asc(), DocumentChunk.id.asc())
        .limit(limit)
        .all()
    )

    return [
        RetrievedContext(
            text=row.chunk_text,
            source=row.document.title,
            document_id=row.document_id,
            file_type=row.document.file_type,
            distance=0.0,
        )
        for row in rows
    ]


def delete_document_and_rebuild(
    document_id: int,
    student_id: int,
    db: Session,
) -> bool:
    """
    Delete a document (and its chunks) then rebuild the FAISS index from
    all remaining chunks across ALL students.

    Returns True if the document was found and deleted, False if not found
    or if it belongs to a different student (ownership check).
    """
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        return False

    # Ownership check — never let one student delete another's document
    if document.student_id != student_id:
        return False

    # Delete from DB (cascades to DocumentChunk rows)
    db.delete(document)
    db.commit()

    # Rebuild FAISS from surviving chunks across all students
    _rebuild_index_from_db(db)

    return True


def _rebuild_index_from_db(db: Session) -> None:
    """
    Re-embed all surviving DocumentChunk rows and rebuild the FAISS index.
    Called after a deletion to purge stale vectors.

    This is O(total_chunks) — acceptable for study-material scale.
    For very large deployments you'd want a deletable index (FAISS IVF
    with IDMap), but FlatL2 + rebuild is simpler and correct.
    """
    all_chunks = db.query(DocumentChunk).all()

    if not all_chunks:
        rebuild(np.empty((0, 384), dtype=np.float32), [])
        return

    texts     = [c.chunk_text for c in all_chunks]
    chunk_ids = [c.id         for c in all_chunks]

    embeddings = _embed(texts)
    rebuild(embeddings, chunk_ids)

    # Update embedding_id for each chunk to match new FAISS positions
    for i, chunk in enumerate(all_chunks):
        chunk.embedding_id = i

    db.commit()
    print(f"[rag_service] Index rebuilt with {len(all_chunks)} chunks.")