"""
import_ductile_json_to_neo4j.py  –  Append ductile iron data to Neo4j.

Run AFTER import_batch_json_to_neo4j.py (which clears the DB first).
This script only appends — it never clears the database.

    python import_batch_json_to_neo4j.py   # clears DB, imports batch
    python import_ductile_json_to_neo4j.py # appends ductile data

Fixes vs original script
──────────────────────────
BUG-1  null values (publisher, page_number, unit, tolerance, standard)
       stored as None on nodes — now stripped.
BUG-2  Material attributes dict stored as JSON string blob — now promoted
       to individual searchable properties (application, pipe_type, purity,
       mass_per_area etc.) matching what retrieval.py expects.
BUG-3  No toString() safety — integer values like year=2017 would crash
       toLower() in retrieval queries — now all numeric props stored as-is
       but coalesce calls in retrieval.py wrap with toString().
BUG-4  'id' property not explicitly stored — MERGE uses it but SET n+=props
       would only store it if it was in props. Now always included.
"""

import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI   = os.getenv("NEO4J_URI")
AUTH  = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

DUCTILE_FILE = "./input_data/data_ductile.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flatten_value(v):
    """
    Flatten lists and dicts to readable strings. Return None for null values
    so they are stripped before being sent to Neo4j.
    """
    if v is None:
        return None
    if isinstance(v, list):
        flat = ", ".join(str(i) for i in v if i is not None)
        return flat if flat else None
    if isinstance(v, dict):
        flat = "; ".join(f"{k}: {val}" for k, val in v.items() if val is not None)
        return flat if flat else None
    return v


def _clean_props(label: str, node_id: str, raw_props: dict) -> dict:
    """
    Build a clean property dict from a ductile node's properties block.

    - Always stores 'id' as a property (critical for MATCH in relationships).
    - Strips all None values.
    - Promotes Material attributes to individual top-level properties.
    - Flattens lists and dicts to strings.
    """
    props: dict = {}

    # Always store id explicitly
    props["id"] = node_id

    # Material: promote attributes dict to individual searchable properties
    if label == "Material":
        attrs = raw_props.get("attributes")
        if isinstance(attrs, dict):
            # Promote each attribute key directly — makes them searchable
            # by the retrieval.py WHERE clause
            for k, v in attrs.items():
                if v is not None:
                    props[k] = str(v)
            # Build a human-readable text summary for the LLM
            parts = []
            if attrs.get("application"):   parts.append(attrs["application"])
            if attrs.get("pipe_type"):     parts.append(f"Pipe type: {attrs['pipe_type']}")
            if attrs.get("mass_per_area"): parts.append(f"Mass: {attrs['mass_per_area']}")
            if attrs.get("purity"):        parts.append(f"Purity: {attrs['purity']}")
            if attrs.get("raw_text"):      parts.append(attrs["raw_text"])
            if parts:
                props["text"] = " | ".join(parts)

    # General property loop — skip 'id' (handled above) and 'attributes'
    SKIP = {"id", "attributes"}
    for k, v in raw_props.items():
        if k in SKIP:
            continue
        v_flat = _flatten_value(v)
        if v_flat is None or v_flat == "":
            continue
        # Don't overwrite keys already promoted from attributes
        if k not in props:
            props[k] = v_flat

    return props


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_ductile_data():
    # Read file
    try:
        with open(DUCTILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Failed to read {DUCTILE_FILE}: {e}")
        return

    nodes = data.get("nodes", [])
    rels  = data.get("relationships", [])
    print(f"📦 Appending {len(nodes)} nodes and {len(rels)} relationships…")

    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session() as session:

        # ── Nodes ─────────────────────────────────────────────────────────────
        node_count = 0
        for node in nodes:
            nid    = node.get("id")
            labels = node.get("labels", [])
            raw    = node.get("properties", {})

            if not nid or not labels:
                continue

            label = labels[0]
            props = _clean_props(label, nid, raw)

            # MERGE on id so re-running is safe (idempotent)
            session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                id=nid, props=props
            )
            node_count += 1

        print(f"  ✅ {node_count} nodes imported")

        # ── Relationships ─────────────────────────────────────────────────────
        rel_count  = 0
        rel_failed = 0
        for rel in rels:
            start = rel.get("start")
            end   = rel.get("end")
            rtype = rel.get("type")

            if not (start and end and rtype):
                continue

            result = session.run(
                f"MATCH (a {{id: $s}}) MATCH (b {{id: $e}}) "
                f"MERGE (a)-[r:{rtype}]->(b)",
                s=start, e=end
            )
            summary = result.consume()
            if summary.counters.relationships_created > 0:
                rel_count += 1
            else:
                # Relationship already existed (MERGE) or nodes not found
                rel_failed += 1

        print(f"  ✅ {rel_count} new relationships created")
        if rel_failed:
            print(f"  ℹ  {rel_failed} relationships already existed or nodes not found")

    driver.close()
    print("\n🎉 Ductile data appended successfully.")


if __name__ == "__main__":
    import_ductile_data()