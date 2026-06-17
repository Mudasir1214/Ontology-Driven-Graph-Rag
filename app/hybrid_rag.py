"""
hybrid_rag.py  –  Hybrid retrieval combining Vector (FAISS) + Graph (Neo4j).

Public API
----------
retrieve_hybrid_context(query, graph_function, top_k=10) -> dict
    Returns:
        {
            "vector":   str,   # formatted vector chunks (for UI panel)
            "graph":    str,   # formatted graph evidence (for UI panel)
            "combined": str,   # merged context ready for LLM system prompt
        }

Design
------
Vector retrieval gives broad semantic coverage — it finds relevant text
even when exact keywords don't match node properties.

Graph retrieval gives structured, relationship-aware evidence — it follows
ontology edges to surface constraints, materials, and cross-standard conflicts
that no vector search can find.

The combined context puts Graph evidence first in the LLM prompt because it
is more structured and reliable. Vector evidence follows as supplementary
factual content. Simple deduplication prevents the same sentence appearing
in both sections.
"""
from __future__ import annotations
from vector_rag import retrieve_vector_context, retrieve_vector_chunks


def _deduplicate_vector(vector_chunks: list[dict], graph_context: str) -> list[dict]:
    """
    Remove vector chunks whose first 120 chars substantially overlap with
    content already present in the graph context string.
    """
    graph_lower = graph_context.lower()
    filtered = []
    for chunk in vector_chunks:
        # Use a 120-char fingerprint from the chunk text
        fingerprint = chunk["text"][:120].strip().lower()
        # If >60 chars of the chunk are already verbatim in graph context, skip it
        if len(fingerprint) > 60 and fingerprint[:60] in graph_lower:
            continue
        filtered.append(chunk)
    return filtered


def _format_vector_section(chunks: list[dict]) -> str:
    """Format deduplicated vector chunks into a readable section string."""
    if not chunks:
        return ""
    lines = []
    for chunk in chunks:
        meta_parts = []
        if chunk.get("chapter"): meta_parts.append(f"Chapter: {chunk['chapter']}")
        if chunk.get("source"):  meta_parts.append(f"Source: {chunk['source']}")
        if chunk.get("module"):  meta_parts.append(f"Module: {chunk['module']}")
        meta_parts.append(f"Score: {chunk['score']:.2f}")
        header = f"[{chunk['rank']}] " + " | ".join(meta_parts)
        lines.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(lines)


def retrieve_hybrid_context(
    query: str,
    graph_function,
    top_k: int = 10,
) -> dict:
    """
    Retrieve from both Vector and Graph, merge into a single context dict.

    Parameters
    ----------
    query          : user's question
    graph_function : callable — retrieve_graph_context from retrieval.py
    top_k          : number of vector chunks to retrieve

    Returns
    -------
    dict with keys: vector (str), graph (str), combined (str)
    """
    # ── Vector retrieval ──────────────────────────────────────────────────────
    try:
        vector_chunks = retrieve_vector_chunks(query, top_k=top_k)
        vector_str    = retrieve_vector_context(query, top_k=top_k)
    except Exception as e:
        vector_chunks = []
        vector_str    = ""
        print(f"Vector retrieval error: {e}")

    # ── Graph retrieval ───────────────────────────────────────────────────────
    try:
        graph_str = graph_function(query)
    except Exception as e:
        graph_str = f"Graph retrieval error: {e}"

    # ── Deduplicate vector against graph ──────────────────────────────────────
    filtered_chunks  = _deduplicate_vector(vector_chunks, graph_str)
    filtered_vec_str = _format_vector_section(filtered_chunks)

    # ── Build combined prompt context ─────────────────────────────────────────
    sections = []

    if graph_str and "error" not in graph_str.lower()[:20]:
        sections.append(
            "=== GRAPH KNOWLEDGE (ontology-structured) ===\n" + graph_str
        )

    if filtered_vec_str:
        sections.append(
            "=== VECTOR KNOWLEDGE (semantic text retrieval) ===\n" + filtered_vec_str
        )
    elif vector_str and not filtered_chunks:
        # Fallback: use raw vector string if dedup removed everything
        sections.append(
            "=== VECTOR KNOWLEDGE (semantic text retrieval) ===\n" + vector_str
        )

    combined = "\n\n" + "\n\n".join(sections) if sections else (
        "No relevant knowledge retrieved from either vector or graph sources."
    )

    return {
        "vector":   vector_str,   # full, for UI panel display
        "graph":    graph_str,    # full, for UI panel display
        "combined": combined,     # merged, for LLM prompt
    }


# ---------------------------------------------------------------------------
# Smoke-test:  python hybrid_rag.py
# ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     from retrieval import retrieve_graph_context

#     tests = [
#         "What are the requirements for spring mounts?",
#         "ductile iron pipe coating requirements",
#         "cable loop vibration",
#     ]
#     for q in tests:
#         print(f"\n{'='*60}\nQUERY: {q}\n{'='*60}")
#         result = retrieve_hybrid_context(q, retrieve_graph_context, top_k=5)
#         print("VECTOR:", result["vector"][:200])
#         print("\nGRAPH:",  result["graph"][:200])
#         print("\nCOMBINED:", result["combined"][:300])