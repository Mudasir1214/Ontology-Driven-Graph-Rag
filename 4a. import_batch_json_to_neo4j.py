"""
import_batch_json_to_neo4j.py  –  Import batch_data into Neo4j for Graph RAG.

ARCHITECTURE:
    Graph RAG indexes ONLY batch_data/*.json (30 structured ontology files).
    data_ductile.json is NOT imported — it duplicates ductile iron rules
    already present in the batch files, and keeping it separate caused
    conflicting rules in the graph that confused retrieval.


Run once (clears DB first, then imports all 30 batch files):
    python import_batch_json_to_neo4j.py

Fixes vs original script
──────────────────────────
BUG-1  ConstraintGroup/Constraint use 'Id' (capital) — id property was
       never stored on the node, breaking all relationships to/from them.
BUG-2  null values stored as None on nodes.
BUG-3  Constraint Value lists stored as raw JSON strings.
BUG-4  ConstraintGroup branches stored as unreadable JSON blob.
BUG-5  workstep/Workstep label inconsistency → unified as WorkStep.
"""

import json
import os
import glob
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI  = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

BATCH_FOLDER = "./input_data/batch_data"

# ── Label map ─────────────────────────────────────────────────────────────────
LABEL_MAP = {
    "document":          "Document",
    "chapter":           "Chapter",
    "module":            "Module",
    "rule":              "Rule",
    "component":         "Component",
    "component_related": "Component",
    "material":          "Material",
    "constraintgroups":  "ConstraintGroup",
    "constraints":       "Constraint",
    "workstep":          "WorkStep",
    "interface":         "Interface",
    "space":             "Space",
    "product":           "Product",
    "supplier":          "Supplier",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_id(item: dict) -> str | None:
    return item.get("id") or item.get("Id")


def _flatten_value(v):
    if v is None:
        return None
    if isinstance(v, list):
        flat = ", ".join(str(i) for i in v if i is not None)
        return flat if flat else None
    if isinstance(v, dict):
        flat = "; ".join(f"{k}: {val}" for k, val in v.items() if val is not None)
        return flat if flat else None
    return v


def _clean_props(node_type: str, item: dict) -> dict:
    props: dict = {}
    nt = node_type.lower().replace("_", "").replace(":", "")

    # Always store id as a property (critical for relationship MATCH)
    nid = _get_id(item)
    if nid:
        props["id"] = nid

    # Material: promote attributes to searchable top-level properties
    if nt == "material":
        attrs = item.get("attributes")
        if isinstance(attrs, dict):
            if attrs.get("raw_text"):
                props["text"] = attrs["raw_text"]
            for k, v in attrs.items():
                if k != "raw_text" and v is not None:
                    props[k] = str(v)

    # ConstraintGroup: make branches human-readable
    if nt in ("constraintgroup", "constraintgroups"):
        branches = item.get("branches")
        if isinstance(branches, list):
            parts = []
            for b in branches:
                expr   = b.get("condition_expression", "")
                constr = ", ".join(b.get("applies_constraints", []))
                parts.append(f"If {expr}: [{constr}]")
            props["branches_text"] = " | ".join(parts)

    SKIP = {"id", "Id", "attributes", "branches"}
    for k, v in item.items():
        if k in SKIP:
            continue
        nk = k.lower()
        if nk == "note": nk = "description"
        v_flat = _flatten_value(v)
        if v_flat is None or v_flat == "":
            continue
        if nk not in props:
            props[nk] = v_flat

    return props


def _run_rel(session, start: str, end: str, rtype: str) -> None:
    session.run(
        f"MATCH (a {{id: $s}}) MATCH (b {{id: $e}}) MERGE (a)-[r:{rtype}]->(b)",
        s=start, e=end
    )


# ── Database operations ───────────────────────────────────────────────────────

def clear_database(session):
    print("🧹 Clearing database…")
    session.run("MATCH (n) DETACH DELETE n")
    print("✅ Database cleared\n")


def import_batch_file(session, file_path: str):
    filename = os.path.basename(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ✗ {filename}: read failed — {e}")
        return

    nodes_container = data.get("nodes")
    if not nodes_container or not isinstance(nodes_container, dict):
        print(f"  ⚠ {filename}: missing or non-dict 'nodes' — skipping")
        return

    node_count = 0
    for key, content in nodes_container.items():
        if not content:
            continue
        label = LABEL_MAP.get(key.lower(), key.capitalize())
        items = content if isinstance(content, list) else [content]
        for item in items:
            if not item:
                continue
            nid = _get_id(item)
            if not nid:
                continue
            props = _clean_props(key, item)
            session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                id=nid, props=props
            )
            node_count += 1

    rels      = data.get("relationships") or data.get("relations") or []
    rel_count = 0
    for rel in rels:
        start = rel.get("from") or rel.get("start")
        end   = rel.get("to")   or rel.get("end")
        rtype = rel.get("type")
        if start and end and rtype:
            _run_rel(session, start, end, rtype)
            rel_count += 1

    print(f"  ✅ {filename}: {node_count} nodes, {rel_count} relationships")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(BATCH_FOLDER):
        print(f"✗ Folder '{BATCH_FOLDER}' not found")
        return

    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session() as session:
        clear_database(session)

        batch_files = sorted(glob.glob(os.path.join(BATCH_FOLDER, "*.json")))
        print(f"📂 Importing {len(batch_files)} batch file(s) from {BATCH_FOLDER}…\n")

        for fp in batch_files:
            import_batch_file(session, fp)

    driver.close()
    print("\n🎉 Import complete.")


if __name__ == "__main__":
    main()