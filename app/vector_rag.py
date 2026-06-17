"""
vector_rag.py  –  FAISS-based semantic retrieval for the RAG workbench.

Expected artefacts (built by your indexing script):
    ./vector_db/faiss.index   – FAISS IndexFlatIP (inner-product) or IndexFlatL2
    ./vector_db/chunks.pkl    – list[dict] with keys:
                                    text      (str)   required
                                    source    (str)   optional – document name
                                    chapter   (str)   optional – chapter / section ID
                                    page      (str)   optional – page number
                                Any plain list[str] also works (legacy format).

Public API
----------
retrieve_vector_context(query, top_k=5, score_threshold=0.0) -> str
    Returns a formatted string ready to be dropped into an LLM system prompt.

retrieve_vector_chunks(query, top_k=5, score_threshold=0.0) -> list[dict]
    Returns the raw ranked chunks with scores attached – useful for the UI
    context panel and for unit tests.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_DB_DIR        = Path("./vector_db")
_INDEX_PATH    = _DB_DIR / "faiss.index"
_CHUNKS_PATH   = _DB_DIR / "chunks.pkl"
_MODEL_NAME    = "sentence-transformers/all-MiniLM-L6-v2"

# Score threshold — kept at 0.0 because relevance filtering is now handled
# by the LLM classifier in relevance_check.py before retrieval runs.
# Raising this threshold caused valid BSM questions with lower semantic
# similarity scores to return no results.
DEFAULT_SCORE_THRESHOLD = 0.0

# ---------------------------------------------------------------------------
# Lazy singletons  (loaded once, reused across calls)
# ---------------------------------------------------------------------------

_index:  faiss.Index | None      = None
_chunks: list[Any]  | None      = None
_model:  SentenceTransformer | None = None


def _load_resources() -> tuple[faiss.Index, list[Any], SentenceTransformer]:
    """Load FAISS index, chunk list, and embedding model (lazy, cached)."""
    global _index, _chunks, _model

    if _index is None:
        if not _INDEX_PATH.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {_INDEX_PATH}. "
                "Run your indexing script first."
            )
        _index = faiss.read_index(str(_INDEX_PATH))

    if _chunks is None:
        if not _CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"Chunks file not found at {_CHUNKS_PATH}. "
                "Run your indexing script first."
            )
        with open(_CHUNKS_PATH, "rb") as fh:
            _chunks = pickle.load(fh)

    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)

    return _index, _chunks, _model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(vec: np.ndarray) -> np.ndarray:
    """L2-normalise a 2-D float32 matrix row-wise (in-place safe copy)."""
    vec = vec.astype("float32")
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)   # avoid division by zero
    return vec / norms


def _is_inner_product_index(idx: faiss.Index) -> bool:
    """
    True when the index uses inner-product metric (cosine after normalisation).
    False when it uses L2 (squared-Euclidean) metric.
    """
    return getattr(idx, "metric_type", faiss.METRIC_L2) == faiss.METRIC_INNER_PRODUCT


def _distance_to_similarity(distances: np.ndarray, is_ip: bool) -> np.ndarray:
    """
    Convert raw FAISS distances to a [0, 1]-ish similarity score.

    • Inner-product (after L2 normalisation)  →  already cosine similarity [-1, 1].
      We clip to [0, 1] so negative similarities (completely unrelated) map to 0.

    • L2 squared distance d  →  similarity = 1 / (1 + d).
      This gives 1.0 for identical vectors and approaches 0 for very distant ones.
    """
    if is_ip:
        return np.clip(distances, 0.0, 1.0)
    else:
        return 1.0 / (1.0 + distances)


def _chunk_text(chunk: Any) -> str:
    """Extract the plain text regardless of whether a chunk is a dict or str."""
    if isinstance(chunk, dict):
        return chunk.get("text") or chunk.get("content") or ""
    return str(chunk)


def _chunk_meta(chunk: Any) -> dict[str, str]:
    """Extract metadata for display in the LLM prompt."""
    if isinstance(chunk, dict):
        return {
            "source":  chunk.get("source",  ""),
            "chapter": chunk.get("chapter", ""),
            "module":  chunk.get("module",  ""),
            "page":    chunk.get("page",    ""),
        }
    return {"source": "", "chapter": "", "module": "", "page": ""}


# ---------------------------------------------------------------------------
# Public retrieval functions
# ---------------------------------------------------------------------------

def retrieve_vector_chunks(
    query: str,
    top_k: int = 5,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> list[dict]:
    """
    Retrieve the *top_k* most semantically relevant chunks for *query*.
    Relevance filtering is handled upstream by the LLM classifier.
    """
    index, chunks, model = _load_resources()

    # Embed & normalise query
    q_emb = model.encode([query], convert_to_numpy=True)
    q_emb = _normalise(q_emb)

    # Retrieve top_k candidates (ask for a few extra to allow threshold filtering)
    fetch_k = min(top_k + 5, len(chunks))
    raw_distances, raw_ids = index.search(q_emb, fetch_k)

    is_ip = _is_inner_product_index(index)
    scores = _distance_to_similarity(raw_distances[0], is_ip)

    results: list[dict] = []
    for faiss_id, score in zip(raw_ids[0], scores):
        # FAISS returns -1 for unfilled slots
        if faiss_id < 0 or faiss_id >= len(chunks):
            continue
        if score < score_threshold:
            continue

        chunk = chunks[faiss_id]
        results.append({
            "text":    _chunk_text(chunk),
            "score":   float(round(score, 4)),
            "rank":    len(results) + 1,
            **_chunk_meta(chunk),
        })

        if len(results) == top_k:
            break

    return results


def retrieve_vector_context(
    query: str,
    top_k: int = 5,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> str:
    """
    Retrieve relevant chunks and format them as a single context string
    ready to be inserted into an LLM system prompt.

    Format per chunk:
        [1] Source: Chapter 3.2 | File: bsm_mechanical.json | Score: 0.87
        <chunk text>

    Returns an empty-hint string when no chunks pass the threshold.
    """
    chunks = retrieve_vector_chunks(query, top_k=top_k, score_threshold=score_threshold)

    if not chunks:
        return ""   # empty string — callers check for this; do NOT return a
                    # "No relevant passages…" sentence because the LLM will read
                    # it as context, say "No information found", then answer from
                    # parametric memory while appearing to cite a missing source.

    lines: list[str] = []
    for chunk in chunks:
        # Build a compact metadata header
        meta_parts: list[str] = []
        if chunk["chapter"]:
            meta_parts.append(f"Chapter: {chunk['chapter']}")
        if chunk["source"]:
            meta_parts.append(f"Source: {chunk['source']}")
        if chunk["page"]:
            meta_parts.append(f"Page: {chunk['page']}")
        meta_parts.append(f"Score: {chunk['score']:.2f}")

        header = f"[{chunk['rank']}] " + " | ".join(meta_parts)
        lines.append(f"{header}\n{chunk['text']}")

    return "\n\n---\n\n".join(lines)