"""
config.py  –  Shared constants, CSS (dark + light themes), and cached connections.
"""
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from neo4j import GraphDatabase

load_dotenv()

# ── Env vars ─────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
NEO4J_URI         = os.getenv("NEO4J_URI")
NEO4J_AUTH        = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))
LLM_MODEL         = "deepseek-chat"

# ── Theme CSS + toggle button ─────────────────────────────────────────────────
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ═══════════════════════════════════════════════════════════════
   DARK THEME  (default — applied to :root / body)
   ═══════════════════════════════════════════════════════════════ */
:root {
    --bg-base:        #0D1117;
    --bg-surface:     #161B22;
    --bg-elevated:    #21262D;
    --border:         #30363D;
    --text-primary:   #C9D1D9;
    --text-secondary: #8B949E;
    --text-muted:     #6E7681;
    --accent:         #58A6FF;
    --accent-hover:   #79C0FF;
    --success:        #22C55E;
    --warning:        #E8A735;
    --danger:         #E24B4A;
    --code-text:      #79C0FF;
    --shadow:         0 4px 24px rgba(0,0,0,0.4);
}

/* ═══════════════════════════════════════════════════════════════
   LIGHT THEME (Triggered when the hidden checkbox is checked)
   ═══════════════════════════════════════════════════════════════ */
body:has(#pure-theme-toggle:checked) {
    --bg-base:        #F6F8FA !important;
    --bg-surface:     #FFFFFF !important;
    --bg-elevated:    #EAEEF2 !important;
    --border:         #D0D7DE !important;
    --text-primary:   #1F2328 !important;
    --text-secondary: #57606A !important;
    --text-muted:     #6E7781 !important;
    --accent:         #0969DA !important;
    --accent-hover:   #0550AE !important;
    --success:        #1A7F37 !important;
    --warning:        #9A6700 !important;
    --danger:         #CF222E !important;
    --code-text:      #0550AE !important;
    --shadow:         0 4px 24px rgba(0,0,0,0.1) !important;
}

/* ═══════════════════════════════════════════════════════════════
   GLOBAL BASE  (uses variables — works for both themes)
   ═══════════════════════════════════════════════════════════════ */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="block-container"] {
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Sans', sans-serif;
    transition: background-color 0.3s ease, color 0.3s ease;
}

#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
    transition: background-color 0.3s ease;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown {
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] .stRadio > label { color: var(--text-secondary) !important; }
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    color: var(--text-primary) !important;
}

/* ── Headings ─────────────────────────────────────────────── */
h1 {
    color: var(--accent) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.5px;
}
h2, h3 { color: var(--text-primary) !important; }
p, span, li, td, th { color: var(--text-primary) !important; }

/* ── Chat messages ────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin-bottom: 8px;
    color: var(--text-primary) !important;
    box-shadow: var(--shadow);
    transition: background-color 0.3s ease, border-color 0.3s ease;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li {
    color: var(--text-primary) !important;
}

/* ── Chat input (cross-platform, both themes) ─────────────── */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div,
[data-testid="stChatInput"] > div > div > div {
    background-color: var(--bg-surface) !important;
    border-color: var(--border) !important;
    transition: background-color 0.3s ease, border-color 0.3s ease;
}
[data-testid="stChatInput"] textarea {
    background-color: var(--bg-surface) !important;
    border: 2px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    caret-color: var(--accent) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s ease, background-color 0.3s ease;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--accent) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-muted) !important;
    opacity: 1 !important;
}
[data-testid="stChatInput"] button {
    background-color: var(--bg-elevated) !important;
    border-color: var(--border) !important;
    color: var(--accent) !important;
    border-radius: 8px !important;
    transition: background-color 0.2s ease;
}
[data-testid="stChatInput"] button:hover {
    background-color: var(--accent) !important;
    color: #FFFFFF !important;
}
[data-testid="stBottom"],
[data-testid="stBottom"] > div {
    background-color: var(--bg-base) !important;
    border-top: 1px solid var(--border) !important;
    transition: background-color 0.3s ease;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-size: 0.85rem;
    font-weight: 500;
    border-radius: 6px 6px 0 0;
    padding: 8px 16px;
    transition: color 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: var(--bg-elevated) !important;
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* ── Buttons & Download Buttons ───────────────────────────── */
.stButton > button,
[data-testid="stDownloadButton"] > button {
    background-color: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.stButton > button:hover,
[data-testid="stDownloadButton"] > button:hover {
    background-color: var(--border) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Code blocks ──────────────────────────────────────────── */
.stCode, pre, code {
    background-color: var(--bg-elevated) !important;
    color: var(--code-text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
    transition: background-color 0.3s ease;
}

/* ── Alerts ───────────────────────────────────────────────── */
.stAlert {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

/* ── Metrics Panel Widgets (Averages Text Color Fix) ───────── */
[data-testid="stMetricValue"] div {
    color: var(--text-primary) !important;
}
[data-testid="stMetricLabel"] p {
    color: var(--text-secondary) !important;
}

/* ═══════════════════════════════════════════════════════════════
   CRITICAL RECTIFICATION FOR EXPANDERS & DATAFRAMES
   ═══════════════════════════════════════════════════════════════ */

/* ── 1. The Expander Layout Fixes ─────────────────────────── */
[data-testid="stExpander"] {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* Force the summary header button layer to clear its default dark skin */
[data-testid="stExpander"] summary {
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
}
[data-testid="stExpander"] summary:hover {
    background-color: var(--bg-elevated) !important;
}

/* Force expanded inner wrapper blocks */
[data-testid="stExpander"] div[data-transition="true"],
[data-testid="stExpander"] div[data-transition="true"] > div {
    background-color: var(--bg-surface) !important;
}

/* Target details labels and secondary items */
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] p,
[data-testid="stExpander"] label {
    color: var(--text-primary) !important;
}

/* Light / Dark textarea matching */
body:has(#pure-theme-toggle:checked) [data-testid="stExpander"] textarea {
    background-color: #FFFFFF !important;
    color: #1F2328 !important;
    border: 1px solid #D0D7DE !important;
}
body:not(:has(#pure-theme-toggle:checked)) [data-testid="stExpander"] textarea {
    background-color: #161B22 !important;
    color: #C9D1D9 !important;
    border: 1px solid #30363D !important;
}


/* ── 2. The Dataframe Container Override (wrapper only —
       cell colours are set in Python via metrics.py Styler,
       NOT here, because st.dataframe paints cells on canvas
       and ignores CSS entirely for cell content) ──────────── */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div {
    border: 1px solid var(--border) !important;
    border-radius: 6px;
}

/* ── Caption / small ──────────────────────────────────────── */
.stCaption, small { color: var(--text-muted) !important; font-size: 0.78rem; }

/* ── Divider ──────────────────────────────────────────────── */
hr { border-color: var(--border) !important; }

/* ── Context badge ────────────────────────────────────────── */
.ctx-badge {
    display: inline-block;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 8px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--accent);
    margin-bottom: 8px;
}

/* ── Mode title bar ───────────────────────────────────────── */
.mode-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0 16px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
}
.mode-icon { font-size: 1.4rem; }
.mode-desc { font-size: 0.82rem; color: var(--text-muted); }

/* ═══════════════════════════════════════════════════════════════
   FIXED THEME TOGGLE BUTTON (Managed with CSS-only Engine)
   ═══════════════════════════════════════════════════════════════ */
/* Hide structural tracking input */
#pure-theme-toggle {
    position: fixed !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Target the label to maintain your beautiful pill layout */
#theme-toggle-btn {
    position: fixed;
    top: 16px;
    right: 20px;
    z-index: 99999999;
    width: 56px;
    height: 28px;
    border-radius: 14px;
    border: 2px solid var(--border);
    cursor: pointer;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    padding: 0 4px;
    transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.2s ease;
    box-shadow: var(--shadow);
}
#theme-toggle-btn:hover {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(88,166,255,0.2);
}

#theme-toggle-knob {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--accent);
    transition: transform 0.3s ease, background 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    line-height: 1;
    transform: translateX(0px);
}

/* Slide knob smoothly when checkbox state triggers light mode */
#pure-theme-toggle:checked + #theme-toggle-btn #theme-toggle-knob {
    transform: translateX(26px);
}

/* Dynamic emoji content adjustment inside the knob container */
#theme-toggle-knob::before {
    content: "🌙";
}
#pure-theme-toggle:checked + #theme-toggle-btn #theme-toggle-knob::before {
    content: "☀️" !important;
}

/* Tooltip label */
#theme-toggle-btn::after {
    content: attr(data-label);
    position: absolute;
    right: 64px;
    top: 50%;
    transform: translateY(-50%);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-muted);
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
}
#theme-toggle-btn:hover::after {
    opacity: 1;
}
</style>

<input type="checkbox" id="pure-theme-toggle" />
<label id="theme-toggle-btn" for="pure-theme-toggle" data-label="Toggle theme" title="Toggle light / dark">
    <div id="theme-toggle-knob"></div>
</label>
"""

# ── Node colours for graph viz ────────────────────────────────────────────────
NODE_COLORS = {
    "Document":        "#EF4444",
    "Chapter":         "#F97316",
    "Rule":            "#22C55E",
    "Component":       "#3B82F6",
    "Module":          "#A855F7",
    "Constraint":      "#06B6D4",
    "ConstraintGroup": "#22D3EE",
    "Material":        "#92400E",
    "WorkStep":        "#EC4899",
}

# ── Cached connections ────────────────────────────────────────────────────────
@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)


def get_llm_client() -> OpenAI:
    """
    Return a fresh OpenAI client on every call.
    NOT cached — caching causes stale HTTP connections after a few requests.
    """
    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=60.0,
        max_retries=2,
    )


@st.cache_data(ttl=300)
def get_visualization_data():
    """Fetch all nodes + edges from Neo4j for the topology view."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            df_nodes = pd.DataFrame([
                r.data() for r in session.run(
                    "MATCH (n) "
                    "RETURN n.id AS ID, "
                    "       COALESCE(n.title, n.name, n.id) AS Label, "
                    "       labels(n)[0] AS Type"
                )
            ])
            df_edges = pd.DataFrame([
                r.data() for r in session.run(
                    "MATCH (a)-[r]->(b) "
                    "RETURN a.id AS Source, type(r) AS Type, b.id AS Target"
                )
            ])
        return df_nodes, df_edges
    except Exception as e:
        st.error(f"Neo4j error: {e}")
        return pd.DataFrame(), pd.DataFrame()