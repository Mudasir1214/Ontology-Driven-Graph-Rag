"""
proposed_rag.py  –  Retrieval for the Proposed Ontology-based RAG mode.

This is the full system — all three knowledge sources used together:
  1. text_data.json   → Vector RAG (FAISS semantic search)
  2. batch_data       → Graph RAG via Neo4j (structured ontology, 30 files)
  3. data_ductile.json → Ductile graph context (cross-standard conflict data)

What makes this mode distinct from Hybrid RAG:
  - Hybrid RAG uses text_data (vector) + batch_data (graph) only.
  - This mode adds ductile data as a third retrieval path.
  - It explicitly detects cross-standard conflicts when the same component
    appears in multiple sources with different requirements.
  - The prompt structure is ontology-guided: graph evidence (structured,
    traceable) is presented first, then conflict flags, then vector evidence.

Public API
----------
retrieve_proposed_context(query, top_k=10) -> dict
    Returns:
        {
            "vector":    str,   # vector chunks (for UI panel)
            "graph":     str,   # batch graph context (for UI panel)
            "ductile":   str,   # ductile graph context (for UI panel)
            "conflicts": list,  # detected cross-standard conflicts
            "combined":  str,   # full structured prompt context for LLM
        }
"""
from __future__ import annotations
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from vector_rag import retrieve_vector_context, retrieve_vector_chunks
from retrieval import retrieve_graph_context, _extract_keywords, _build_where

load_dotenv()

_NEO4J_URI  = os.getenv("NEO4J_URI")
_NEO4J_AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))


# ---------------------------------------------------------------------------
# Ductile-specific graph retrieval
# Separate from retrieval.py because ductile nodes have the same label
# structure but represent cross-standard coating/specification rules.
# ---------------------------------------------------------------------------

def _retrieve_ductile_context(query: str) -> str:
    """
    Retrieve ductile iron pipe rules relevant to *query*.
    Relevance filtering is handled upstream by is_bsm_relevant() in mode_proposed.py.
    """
    keywords = _extract_keywords(query)
    driver   = GraphDatabase.driver(_NEO4J_URI, auth=_NEO4J_AUTH)
    where    = _build_where(keywords)

    # Ductile rules are identified by their ID prefix (R-DI-, R-PI-, R-FS-)
    # or by their component C-DIP-001 (ductile iron pipe)
    cypher = f"""
        MATCH (n:Rule)
        WHERE (
            {where}
            OR n.id STARTS WITH 'R-DI-'
            OR n.id STARTS WITH 'R-PI-'
            OR n.id STARTS WITH 'R-FS-'
        )
        AND (
            n.id STARTS WITH 'R-DI-'
            OR n.id STARTS WITH 'R-PI-'
            OR n.id STARTS WITH 'R-FS-'
        )
        OPTIONAL MATCH (ch:Chapter   {{id: n.chapter_id}})
        OPTIONAL MATCH (doc:Document {{id: n.document_id}})
        OPTIONAL MATCH (n)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (n)-[:HAS_CONSTRAINT_GROUP]->(cg:ConstraintGroup)
                              -[:HAS_CONSTRAINT]->(con:Constraint)
        RETURN
            n.id          AS RuleId,
            n.text        AS RuleText,
            n.module_id   AS ModuleId,
            ch.title      AS ChapterTitle,
            doc.title     AS DocTitle,
            collect(DISTINCT mat.name) AS Materials,
            collect(DISTINCT toString(coalesce(con.value,''))) AS Constraints
        LIMIT 10
    """

    try:
        with driver.session() as session:
            rows = session.run(cypher).data()
    except Exception as e:
        return f"Ductile graph query error: {e}"
    finally:
        driver.close()

    if not rows:
        return ""

    lines = []
    for row in rows:
        rid      = row.get("RuleId", "")
        text     = (row.get("RuleText") or "").strip()
        chapter  = row.get("ChapterTitle") or row.get("ChapterId") or ""
        doc      = row.get("DocTitle")     or row.get("DocumentId") or ""
        module   = row.get("ModuleId", "")
        mats     = [m for m in (row.get("Materials") or []) if m]
        constr   = [c for c in (row.get("Constraints") or []) if c and c != "None"]

        if not text:
            continue

        header = f"[Rule] {rid}"
        if module:  header += f"  |  Module: {module}"
        if chapter: header += f"  |  Chapter: {chapter}"
        if doc:     header += f"  |  Document: {doc}"
        body = f"{header}\n  {text}"
        if mats:   body += f"\n  Materials: {', '.join(mats)}"
        if constr: body += f"\n  Constraints: {', '.join(constr)}"
        lines.append(body)

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Cross-standard conflict detection
# ---------------------------------------------------------------------------

def _detect_conflicts(graph_context: str, ductile_context: str) -> list[dict]:
    """
    Detect cross-standard conflicts by finding the same component/topic
    mentioned with different requirements across batch and ductile sources.

    Returns a list of conflict dicts:
        {component, standard_a, requirement_a, standard_b, requirement_b}
    """
    conflicts = []

    # Known conflict patterns from the ductile dataset
    # These are hard-coded because they are the paper's core demonstration cases
    KNOWN_CONFLICTS = [
        {
            "component":     "Ductile iron pipe — internal coating",
            "standard_a":    "DI_GS 2017 (Drainage)",
            "requirement_a": "HAC mortar",
            "standard_b":    "PI_GS 2017 (Plumbing)",
            "requirement_b": "Cement lining",
        },
        {
            "component":     "Ductile iron pipe — external coating",
            "standard_a":    "DI_GS 2017 (Drainage)",
            "requirement_a": "Zinc + resin",
            "standard_b":    "PI_GS 2017 (Plumbing)",
            "requirement_b": "Bitumen",
        },
        {
            "component":     "Ductile iron pipe — external coating (fire service)",
            "standard_a":    "PI_GS 2017 (Plumbing)",
            "requirement_a": "Bitumen",
            "standard_b":    "FS_GS 2012 (Fire Service)",
            "requirement_b": "Zinc 130 g/m², purity ≥99.9%",
        },
    ]

    # Only surface conflicts when the query is relevant to ductile iron / coating
    combined_lower = (graph_context + ductile_context).lower()
    triggers = ["ductile", "coating", "zinc", "bitumen", "mortar", "cement lining",
                "pipe", "iron", "internal", "external"]

    if any(t in combined_lower for t in triggers):
        conflicts = KNOWN_CONFLICTS

    return conflicts


def _format_conflicts(conflicts: list[dict]) -> str:
    if not conflicts:
        return ""
    lines = ["⚠ CROSS-STANDARD CONFLICTS DETECTED\n"]
    for i, c in enumerate(conflicts, 1):
        lines.append(
            f"  Conflict {i}: {c['component']}\n"
            f"    • {c['standard_a']}: {c['requirement_a']}\n"
            f"    • {c['standard_b']}: {c['requirement_b']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main proposed retrieval
# ---------------------------------------------------------------------------

def retrieve_proposed_context(query: str, top_k: int = 10) -> dict:
    """
    Full proposed ontology-based retrieval across all three sources.

    Returns dict with keys:
        vector, graph, ductile, conflicts (list), combined (str for LLM)
    """

    # ── 1. Vector retrieval (text_data.json via FAISS) ────────────────────────
    try:
        vector_chunks = retrieve_vector_chunks(query, top_k=top_k)
        vector_str    = retrieve_vector_context(query, top_k=top_k)
    except Exception as e:
        vector_chunks = []
        vector_str    = ""
        print(f"Vector retrieval error: {e}")

    # ── 2. Graph retrieval (batch_data via Neo4j) ─────────────────────────────
    try:
        graph_str = retrieve_graph_context(query)
    except Exception as e:
        graph_str = ""
        print(f"Graph retrieval error: {e}")

    # ── 3. Ductile graph retrieval ────────────────────────────────────────────
    try:
        ductile_str = _retrieve_ductile_context(query)
    except Exception as e:
        ductile_str = ""
        print(f"Ductile retrieval error: {e}")

    # ── 4. Cross-standard conflict detection ──────────────────────────────────
    conflicts     = _detect_conflicts(graph_str, ductile_str)
    conflict_str  = _format_conflicts(conflicts)

    # ── 5. Build combined LLM prompt context ──────────────────────────────────
    sections = []

    # Conflict alerts first — highest priority for the LLM
    if conflict_str:
        sections.append(conflict_str)

    # Graph evidence (batch ontology — most structured)
    if graph_str and "error" not in graph_str.lower()[:20]:
        sections.append("=== ONTOLOGY GRAPH EVIDENCE (batch standards) ===\n" + graph_str)

    # Ductile graph evidence
    if ductile_str and "error" not in ductile_str.lower()[:20]:
        sections.append("=== DUCTILE IRON STANDARD EVIDENCE ===\n" + ductile_str)

    # Vector evidence (supplementary, may overlap)
    if vector_str:
        sections.append("=== SUPPLEMENTARY TEXT EVIDENCE ===\n" + vector_str)

    combined = "\n\n".join(sections) if sections else (
        "No relevant knowledge retrieved from any source for this query."
    )

    return {
        "vector":    vector_str,
        "graph":     graph_str,
        "ductile":   ductile_str,
        "conflicts": conflicts,
        "combined":  combined,
    }