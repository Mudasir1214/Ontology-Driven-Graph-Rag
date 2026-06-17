"""
modes/mode_graph.py  –  Mode 3: Graph-Enhanced RAG (Neo4j)
"""
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from config import NODE_COLORS, get_visualization_data
from retrieval import retrieve_graph_context
from components.ui import mode_header, render_history, stream_llm, context_panel
from components.metrics import render_metrics_tab, log_answer
from relevance_check import is_bsm_relevant

HISTORY_KEY = "history_graph"
CTX_LOG_KEY = "ctx_log_graph"
METRICS_KEY = "metrics_graph"

SYSTEM_TEMPLATE = """You are a hospital BSM expert.
Answer based on the graph context below.

Rules:
1. Quote rule IDs, chapter titles, and document names exactly as provided.
2. EDITION AWARENESS: Each rule shows its Document field including the edition year
   in parentheses (e.g. "2022 edition", "2012 edition"). Use this to correctly
   attribute rules to their edition. Never assume a rule applies to an edition
   not stated in its Document field.
3. If asked whether a specific edition mentions something, check the Document
   field of each retrieved rule carefully. Only confirm a mention if the rule's
   document edition matches the edition being asked about.
4. REASON from the evidence: if rules from a specific edition are shown and the
   item in question does not appear, state it is not found in that edition.
5. If the context has absolutely no relevant content, say:
   "No information found in retrieved documents."

Context:
{context}
"""

GREETING_SYSTEM = """You are a helpful assistant for a hospital Building Services \
Maintenance (BSM) engineering knowledge system. Respond naturally to greetings \
and general questions. Let the user know you can answer technical BSM questions \
about mechanical, electrical, fire protection, plumbing and drainage standards."""


def _build_graph_widgets(df_nodes, df_edges):
    nodes, edges = [], []
    seen_ids, seen_edges = set(), set()
    for _, row in df_nodes.iterrows():
        nid = str(row["ID"])
        if nid in seen_ids or nid == "None":
            continue
        seen_ids.add(nid)
        label = str(row["Label"])
        ntype = row["Type"]
        nodes.append(Node(
            id=nid,
            label=(label[:15] + "…" if len(label) > 15 else label),
            title=f"[{ntype}] {label}",
            size=25 if ntype == "Rule" else 18,
            color=NODE_COLORS.get(ntype, "#9E9E9E"),
            font={"color": "#C9D1D9", "size": 12, "face": "IBM Plex Mono"},
        ))
    for _, row in df_edges.iterrows():
        src, tgt = str(row["Source"]), str(row["Target"])
        sig = f"{src}-{tgt}"
        if sig not in seen_edges and src in seen_ids and tgt in seen_ids:
            seen_edges.add(sig)
            edges.append(Edge(source=src, target=tgt, color="#30363D", type="arrow"))
    return nodes, edges


def render() -> None:
    mode_header(
        icon="🕸️",
        title="Mode 3 · Graph RAG",
        description="Ontology-guided seed node retrieval → subgraph expansion via Neo4j.",
    )

    for key in [CTX_LOG_KEY, METRICS_KEY]:
        if key not in st.session_state:
            st.session_state[key] = []

    t_chat, t_ctx, t_metrics, t_viz, t_data = st.tabs([
        "💬 Chat", "🔍 Retrieved Knowledge", "📈 Metrics", "🕸️ Topology", "📊 Raw Data",
    ])

    with t_chat:
        render_history(HISTORY_KEY)

        if prompt := st.chat_input("Ask complex engineering questions…"):
            st.session_state[HISTORY_KEY].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        if not is_bsm_relevant(prompt):
                            answer = stream_llm(GREETING_SYSTEM, prompt)
                        else:
                            with st.spinner("Reasoning on graph…"):
                                context = retrieve_graph_context(prompt)

                            if context:
                                st.session_state[CTX_LOG_KEY].append(
                                    {"question": prompt, "context": context}
                                )
                            answer = stream_llm(SYSTEM_TEMPLATE.format(context=context or ""), prompt)

                        st.session_state[HISTORY_KEY].append(
                            {"role": "assistant", "content": answer}
                        )
                        log_answer(METRICS_KEY, prompt, answer, context if is_bsm_relevant(prompt) else "")
                    except Exception as e:
                        st.error(f"Graph RAG error: {e}")

    with t_ctx:
        st.subheader("Retrieved Graph Knowledge")
        log = st.session_state.get(CTX_LOG_KEY, [])
        if not log:
            st.caption("No retrieval yet — ask a BSM question in the Chat tab.")
        else:
            for i, entry in enumerate(reversed(log)):
                q_num = len(log) - i
                with st.expander(
                    f"Q{q_num}: {entry['question'][:80]}{'…' if len(entry['question']) > 80 else ''}",
                    expanded=(i == 0),
                ):
                    context_panel(f"GRAPH · Q{q_num} paths", entry["context"])

    with t_metrics:
        render_metrics_tab(METRICS_KEY)

    with t_viz:
        st.subheader("Knowledge Graph Topology")
        st.caption("🔴 Document · 🟠 Chapter · 🟢 Rule · 🔵 Component · 🟣 Module · 🟤 Material")
        df_nodes, df_edges = get_visualization_data()
        if not df_nodes.empty:
            nodes, edges = _build_graph_widgets(df_nodes, df_edges)
            agraph(nodes=nodes, edges=edges, config=Config(
                width=1200, height=720, directed=True, physics=True, fit=True,
                gravity=-1000, centralGravity=0.6, springLength=70,
                nodeHighlightBehavior=True, backgroundColor="#0D1117",
            ))
        else:
            st.warning("No data available in Neo4j.")

    with t_data:
        df_nodes, _ = get_visualization_data()
        st.dataframe(df_nodes, width='stretch')