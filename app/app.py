"""
app.py  –  RAG Intelligent Workbench entry point.

Run with:
    streamlit run app.py
"""
import streamlit as st
from config import APP_CSS, get_neo4j_driver

import modes.mode_baseline as mode_baseline
import modes.mode_vector   as mode_vector
import modes.mode_graph    as mode_graph
import modes.mode_hybrid   as mode_hybrid
import modes.mode_proposed_ontology as mode_proposed

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="RAG Intelligent Workbench",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

# ── Session-state defaults ────────────────────────────────────────────────────
# Every key used by any mode must be listed here so Streamlit initialises it
# before the first render, avoiding KeyError on first use.
_STATE_DEFAULTS = {
    # Chat histories
    "history_pure":     [],
    "history_vector":   [],
    "history_graph":    [],
    "history_hybrid":   [],
    "history_proposed": [],

    # Per-question context logs (list of dicts, one per question)
    "ctx_log_vector":   [],
    "ctx_log_graph":    [],
    "ctx_log_hybrid":   [],
    "ctx_log_proposed": [],

    # Answer log (baseline only)
    "log_baseline":     [],

    # Metrics logs
    "metrics_baseline": [],
    "metrics_vector":   [],
    "metrics_graph":    [],
    "metrics_hybrid":   [],
    "metrics_proposed": [],
}

for key, default in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────────────────
MODES = {
    "1 · Baseline (Pure LLM)":       mode_baseline,
    "2 · Vector RAG":                mode_vector,
    "3 · Graph RAG":                 mode_graph,
    "4 · Hybrid RAG":                mode_hybrid,
    "5 · Proposed (Ontology-based)": mode_proposed,
}

with st.sidebar:
    st.markdown("## 🧬 RAG Workbench")
    st.divider()

    selected = st.radio(
        "Architecture",
        list(MODES.keys()),
        label_visibility="collapsed",
    )
    st.divider()

    # Neo4j status indicator
    try:
        with get_neo4j_driver().session() as s:
            s.run("RETURN 1")
        st.success("Neo4j · connected", icon="🟢")
    except Exception as e:
        st.error(f"Neo4j · {e}", icon="🔴")

    st.divider()

    if st.button("🧹 Clear all history"):
        for key, default in _STATE_DEFAULTS.items():
            st.session_state[key] = type(default)()
        st.rerun()

# ── Render selected mode ──────────────────────────────────────────────────────
MODES[selected].render()