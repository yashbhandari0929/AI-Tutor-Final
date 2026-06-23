"""
rag/faiss_store.py

Singleton FAISS index manager.

Design decisions:
- FlatL2 index: exact search, no approximation. Fine for study-material
  scale (thousands of chunks per student, not millions).
- append-only: FAISS flat indices don't support deletion. When a Document
  is deleted we rebuild the index from the remaining chunks in the DB.
  This keeps the implementation simple and correct.
- chunk_map: a list where position i holds the DocumentChunk.id whose
  embedding lives at FAISS row i. This is what lets us go from a FAISS
  search result (an integer row index) back to the actual chunk text and
  its owning student_id.
- Both the index and the chunk_map are persisted to disk so they survive
  server restarts without re-embedding everything.
"""

import os
import json
import threading
import numpy as np

# faiss-cpu must be installed: pip install faiss-cpu
import faiss

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH  = os.path.join(_BASE_DIR, "faiss.index")
MAP_PATH    = os.path.join(_BASE_DIR, "chunk_map.json")

# Embedding dimension produced by all-MiniLM-L6-v2
EMBEDDING_DIM = 384

# ── Module-level singletons ───────────────────────────────────────────────────
# Initialised by _load() which is called once at import time (i.e. at server
# startup). After that every request reads/writes these objects directly.
_index:     faiss.IndexFlatL2 | None = None
_chunk_map: list[int]                = []   # position → DocumentChunk.id
_lock = threading.Lock()                    # guards writes (adds + rebuilds)


# ── Internal bootstrap ────────────────────────────────────────────────────────

def _load() -> None:
    """
    Load index + map from disk if they exist, otherwise create a fresh
    empty index. Called once at module import.
    """
    global _index, _chunk_map

    if os.path.exists(INDEX_PATH) and os.path.exists(MAP_PATH):
        try:
            _index = faiss.read_index(INDEX_PATH)
            with open(MAP_PATH, "r") as f:
                _chunk_map = json.load(f)
            print(
                f"[faiss_store] Loaded index with {_index.ntotal} vectors "
                f"and {len(_chunk_map)} chunk map entries."
            )
            return
        except Exception as exc:
            print(f"[faiss_store] WARNING: could not load index from disk ({exc}). "
                  "Creating a fresh index.")

    _index     = faiss.IndexFlatL2(EMBEDDING_DIM)
    _chunk_map = []
    print("[faiss_store] Created fresh FAISS FlatL2 index.")


def _save() -> None:
    """Persist index and map to disk. Must be called inside _lock."""
    faiss.write_index(_index, INDEX_PATH)
    with open(MAP_PATH, "w") as f:
        json.dump(_chunk_map, f)


# ── Public API ────────────────────────────────────────────────────────────────

def add_embeddings(embeddings: np.ndarray, chunk_ids: list[int]) -> list[int]:
    """
    Add a batch of embeddings to the index.

    Parameters
    ----------
    embeddings : np.ndarray, shape (n, EMBEDDING_DIM), dtype float32
    chunk_ids  : list of DocumentChunk.id values, one per embedding row

    Returns
    -------
    List of FAISS row positions assigned to each embedding (i.e. the
    values that should be stored in DocumentChunk.embedding_id).
    """
    if len(embeddings) != len(chunk_ids):
        raise ValueError(
            f"embeddings ({len(embeddings)}) and chunk_ids ({len(chunk_ids)}) "
            "must have the same length."
        )

    embeddings = np.array(embeddings, dtype=np.float32)

    with _lock:
        start_pos = _index.ntotal          # next available row index
        _index.add(embeddings)
        positions = list(range(start_pos, _index.ntotal))
        _chunk_map.extend(chunk_ids)
        _save()

    return positions


def search(query_embedding: np.ndarray, top_k: int = 10) -> list[dict]:
    """
    Search the index for the top_k nearest neighbours.

    Returns a list of dicts:
        { "chunk_id": int, "distance": float }
    sorted by ascending distance (closest first).

    We intentionally return more results than the caller needs (top_k=10
    by default) so that the caller can filter to the current student's
    chunks and still end up with up to 5 relevant results.
    """
    if _index.ntotal == 0:
        return []

    query_embedding = np.array([query_embedding], dtype=np.float32)
    k = min(top_k, _index.ntotal)

    distances, indices = _index.search(query_embedding, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:           # FAISS padding value when k > ntotal
            continue
        if idx >= len(_chunk_map):
            continue            # stale index after a rebuild race (shouldn't happen)
        results.append({
            "chunk_id": _chunk_map[idx],
            "distance": float(dist),
        })

    return results


def rebuild(embeddings: np.ndarray, chunk_ids: list[int]) -> None:
    """
    Replace the entire index with a fresh one built from the given
    embeddings. Called after a document is deleted so stale vectors
    are removed.

    Parameters
    ----------
    embeddings : np.ndarray, shape (n, EMBEDDING_DIM) — may be empty
    chunk_ids  : matching list of DocumentChunk.id values
    """
    global _index, _chunk_map

    new_index = faiss.IndexFlatL2(EMBEDDING_DIM)

    if len(embeddings) > 0:
        embeddings = np.array(embeddings, dtype=np.float32)
        new_index.add(embeddings)

    with _lock:
        _index     = new_index
        _chunk_map = list(chunk_ids)
        _save()

    print(
        f"[faiss_store] Rebuilt index: {new_index.ntotal} vectors, "
        f"{len(chunk_ids)} chunk map entries."
    )


def total_vectors() -> int:
    """Return the number of vectors currently in the index."""
    return _index.ntotal if _index is not None else 0


# ── Bootstrap on import ───────────────────────────────────────────────────────
_load()