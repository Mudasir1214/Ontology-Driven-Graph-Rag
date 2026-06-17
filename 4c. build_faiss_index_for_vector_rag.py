"""
build_faiss_index.py  –  Build the FAISS vector index for Vector RAG.

ARCHITECTURE:
    Vector RAG indexes ONLY text_data.json (30 plain-text summaries).
    Graph RAG indexes ONLY batch_data/*.json (structured ontology nodes → Neo4j).
    Hybrid RAG = Vector RAG (text_data) + Graph RAG (batch_data) combined.

    data_ductile.json is NOT indexed here — it belongs exclusively to Neo4j
    (imported separately via import_to_neo4j.py) and is not part of this system.

Input:
    ./input_data/text_data.json   {"entries": [{text, module, chapter}, ...]}

Output:
    ./app/vector_db/faiss.index
    ./app/vector_db/chunks.pkl        list[dict] with keys: text, source, chapter, module, page
"""

import json
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TEXT_DATA_FILE = Path("./input_data/text_data.json")

VECTOR_DB_DIR  = Path("./app/vector_db")
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = VECTOR_DB_DIR / "faiss.index"
CHUNK_PATH = VECTOR_DB_DIR / "chunks.pkl"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Chunk builder
# ---------------------------------------------------------------------------

def _chunk(text: str, source: str, chapter: str = "",
           module: str = "", page: str = "") -> dict:
    return {
        "text":    text.strip(),
        "source":  source,
        "chapter": chapter,
        "module":  module,
        "page":    str(page) if page else "",
    }


# ---------------------------------------------------------------------------
# Load text_data.json — one chunk per entry, plain text, use directly
# ---------------------------------------------------------------------------

chunks: list[dict] = []

print("Loading text_data.json …")

if not TEXT_DATA_FILE.exists():
    print(f"  ✗  {TEXT_DATA_FILE} not found — cannot build index")
    raise SystemExit(1)

with open(TEXT_DATA_FILE, "r", encoding="utf-8") as fh:
    data = json.load(fh)

entries = data.get("entries", [])
for item in entries:
    text = item.get("text", "").strip()
    if not text:
        continue
    chunks.append(_chunk(
        text    = text,
        source  = "text_data.json",
        chapter = str(item.get("chapter", "")),
        module  = str(item.get("module",  "")),
        page    = str(item.get("page",    "")),
    ))

print(f"  ✓  {len(chunks)} chunks from {len(entries)} entries")

if not chunks:
    print("  ✗  No valid entries found in text_data.json")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------------

print(f"\nLoading model: {MODEL_NAME} …")
model = SentenceTransformer(MODEL_NAME)

print("Generating embeddings …")
embeddings = model.encode(
    [c["text"] for c in chunks],
    convert_to_numpy=True,
    show_progress_bar=True,
    batch_size=64,
)
embeddings = np.array(embeddings, dtype=np.float32)

# ---------------------------------------------------------------------------
# Build FAISS IndexFlatL2
# ---------------------------------------------------------------------------

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

faiss.write_index(index, str(INDEX_PATH))
with open(CHUNK_PATH, "wb") as fh:
    pickle.dump(chunks, fh)

print("\n" + "=" * 50)
print("FAISS INDEX BUILD COMPLETE")
print("=" * 50)
print(f"  Source         : text_data.json only")
print(f"  Total chunks   : {len(chunks)}")
print(f"  Embedding dim  : {embeddings.shape[1]}")
print(f"  Index saved    : {INDEX_PATH}")
print(f"  Chunks saved   : {CHUNK_PATH}")
print(f"\nNote: text data has been processed for Vector RAG.")