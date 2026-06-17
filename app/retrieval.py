"""
retrieval.py  –  Graph-RAG retrieval, aligned with import_to_neo4j.py schema.

Property names actually stored on nodes (after import_to_neo4j.py):
    Rule           : id, text, module_id, chapter_id, document_id
    Chapter        : id, title
    Document       : id, title, year, version
    Module         : id, name
    Component      : id, name, ifc_class
    Material       : id, name, text, application, pipe_type, attr_*
    Constraint     : id, type, operator, value, description (was 'note')
    ConstraintGroup: id, description, logic, rule_id, branches_text
    WorkStep       : id, name, method, description
"""
from __future__ import annotations
from config import get_neo4j_driver

_STOP_WORDS = frozenset([
    "does", "the", "include", "any", "if", "not", "where", "are", "they",
    "defined", "what", "is", "in", "install", "a", "an", "of", "for", "to",
    "with", "and", "or", "how", "can", "do", "has", "have", "that", "this",
    "which", "when", "should", "would", "will", "be", "been", "its",
    "please", "tell", "me", "give", "show", "list", "explain",
])


def _extract_keywords(query: str) -> list[str]:
    tokens = query.lower().replace("?", "").replace(",", "").split()
    keywords = [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]
    return keywords or ["pipework"]


def _extract_keywords(query: str) -> list[str]:
    tokens = query.lower().replace("?", "").replace(",", "").split()
    keywords = [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]
    return keywords or ["pipework"]


def _build_where(keywords: list[str]) -> str:
    """
    Build a Cypher WHERE clause covering every property that could hold
    searchable text, aligned with what import_to_neo4j.py actually stores.

    Every coalesce() is wrapped in toString() because some properties store
    integers (e.g. Constraint.value=50, Document.year=2022) and toLower()
    crashes Neo4j when given a non-string value.
    """
    conditions = []
    for k in keywords:
        k_safe = k.replace("'", "").replace("\\", "")
        conditions.append(
            # Core identity / label fields
            f"toLower(toString(coalesce(n.name,'')))           CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.title,'')))          CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.id,'')))             CONTAINS '{k_safe}' OR "
            # Rule fields
            f"toLower(toString(coalesce(n.text,'')))           CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.module_id,'')))      CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.chapter_id,'')))     CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.document_id,'')))    CONTAINS '{k_safe}' OR "
            # Constraint fields
            f"toLower(toString(coalesce(n.description,'')))    CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.value,'')))          CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.type,'')))           CONTAINS '{k_safe}' OR "
            # Material fields
            f"toLower(toString(coalesce(n.application,'')))    CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.pipe_type,'')))      CONTAINS '{k_safe}' OR "
            # ConstraintGroup / WorkStep
            f"toLower(toString(coalesce(n.branches_text,'')))  CONTAINS '{k_safe}' OR "
            f"toLower(toString(coalesce(n.method,'')))         CONTAINS '{k_safe}'"
        )
    return "(" + ") OR (".join(conditions) + ")"


def retrieve_graph_context(query: str) -> str:
    """
    Return formatted graph evidence for *query*.
    Relevance filtering is handled upstream by the LLM classifier.
    """
    driver   = get_neo4j_driver()
    keywords = _extract_keywords(query)
    where    = _build_where(keywords)

    # ── Query A: direct Rule hits with full metadata ──────────────────────────
    cypher_rules = f"""
        MATCH (n:Rule)
        WHERE {where}
        OPTIONAL MATCH (ch:Chapter   {{id: n.chapter_id}})
        OPTIONAL MATCH (doc:Document {{id: n.document_id}})
        RETURN
            n.id          AS RuleId,
            n.text        AS RuleText,
            n.module_id   AS ModuleId,
            n.chapter_id  AS ChapterId,
            n.document_id AS DocumentId,
            ch.title      AS ChapterTitle,
            doc.title     AS DocTitle,
            doc.year      AS DocYear,
            doc.version   AS DocVersion
        LIMIT 10
    """

    # ── Query B: seed nodes + neighbours ─────────────────────────────────────
    cypher_seed = f"""
        MATCH (n)
        WHERE {where}
        OPTIONAL MATCH (n)-[*1..2]-(nb)
        WHERE nb:Rule OR nb:Constraint
           OR nb:ConstraintGroup OR nb:Material OR nb:WorkStep
        RETURN
            labels(n)[0]                                              AS SeedType,
            coalesce(n.name, n.title, n.id)                           AS SeedName,
            toString(coalesce(n.text, n.description, n.method, ''))   AS SeedContent,
            n.id                                                      AS SeedId,
            collect(DISTINCT {{
                type:    labels(nb)[0],
                id:      coalesce(nb.id, ''),
                name:    coalesce(nb.name, nb.title, nb.id, ''),
                content: toString(coalesce(nb.text, nb.description,
                                           nb.value, nb.method, ''))
            }})                                                       AS Neighbours
        LIMIT 15
    """

    try:
        with driver.session() as session:
            rule_rows = session.run(cypher_rules).data()
            seed_rows = session.run(cypher_seed).data()
    except Exception as e:
        return f"Graph query error: {e}"

    lines: list[str] = []
    seen:  set[str]  = set()

    def _add(text: str, key: str) -> None:
        if key not in seen and text.strip():
            seen.add(key)
            lines.append(text)

    # ── Format Rule hits ──────────────────────────────────────────────────────
    for row in rule_rows:
        rid  = row.get("RuleId", "")
        text = (row.get("RuleText") or "").strip()
        if not text:
            continue
        chapter = row.get("ChapterTitle") or row.get("ChapterId") or ""
        doc     = row.get("DocTitle")     or row.get("DocumentId") or ""
        module  = row.get("ModuleId", "")
        year    = row.get("DocYear",    "")
        version = row.get("DocVersion", "")

        header = f"[Rule] {rid}"
        if module:  header += f"  |  Module: {module}"
        if chapter: header += f"  |  Chapter: {chapter}"
        if doc:
            edition = f"{doc}"
            if version: edition += f" ({version})"
            elif year:  edition += f" ({year} edition)"
            header += f"  |  Document: {edition}"
        _add(f"{header}\n  {text}", rid)

    # ── Format seed nodes + neighbours ───────────────────────────────────────
    for row in seed_rows:
        seed_type    = row.get("SeedType", "")
        seed_name    = (row.get("SeedName")    or "").strip()
        seed_content = (row.get("SeedContent") or "").strip()
        seed_id      = (row.get("SeedId")      or "").strip()

        # Seed node itself (skip Rules — already formatted above)
        if seed_content and seed_type != "Rule":
            label = f"[{seed_type}] {seed_name}" if seed_name != seed_id else f"[{seed_type}] {seed_id}"
            _add(f"{label}\n  {seed_content}", seed_id + "_seed")
        elif seed_type == "Chapter" and seed_name:
            _add(f"[Chapter] {seed_name}", seed_id + "_ch")

        # Neighbours
        for nb in (row.get("Neighbours") or []):
            nb_id      = (nb.get("id")      or "").strip()
            nb_type    = (nb.get("type")    or "Node")
            nb_name    = (nb.get("name")    or "").strip()
            nb_content = (nb.get("content") or "").strip()

            if not nb_id or nb_id in seen:
                continue

            display = nb_name if nb_name and nb_name != nb_id else nb_id
            if nb_content:
                _add(f"[{nb_type}] {display}\n  {nb_content}", nb_id)
            elif display:
                _add(f"[{nb_type}] {display}", nb_id)

    return "\n\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Smoke-test:  python retrieval.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        "What are the requirements for spring mounts?",
        "copper pipe jointing",
        "cable loop vibration equipment",
        "ductile iron pipe coating",
        "drainage sump pump",
        "HAC mortar internal coating",
        "zinc coating purity",
    ]
    for q in tests:
        print(f"\n{'='*60}\nQUERY: {q}\n{'='*60}")
        print(retrieve_graph_context(q)[:500])