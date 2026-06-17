"""
modes/mode_hybrid.py  –  Mode 4: Hybrid RAG (Vector + Graph)
"""
import streamlit as st
from hybrid_rag import retrieve_hybrid_context
from retrieval import retrieve_graph_context
from components.ui import mode_header, render_history, stream_llm, context_panel
from components.metrics import render_metrics_tab, log_answer
from relevance_check import is_bsm_relevant

HISTORY_KEY = "history_hybrid"
CTX_LOG_KEY = "ctx_log_hybrid"
METRICS_KEY = "metrics_hybrid"

SYSTEM_TEMPLATE = """You are an expert Building Services Engineer.
Answer using the retrieved knowledge below.

Rules:
1. Use GRAPH KNOWLEDGE for structured rules and constraints.
2. Use VECTOR KNOWLEDGE for document text, edition years, and chapter context.
3. EDITION ATTRIBUTION: The Document field in graph rules includes the edition year.
   Vector chapter IDs (J001, J002 etc.) also identify specific editions.
   Always attribute rules to the correct edition before drawing conclusions.
4. Cite chapter IDs, rule IDs, and document edition years in your answer.
5. Quote numerical values exactly as stated.
6. Reason from all evidence together — if the evidence shows what IS in an edition,
   you can conclude what is NOT in that edition.
7. End your answer with a clear conclusion. Do NOT add "No information found"
   after you have already provided a full answer — this is contradictory.
8. Only say "No information found" if the context has no relevant content at all.

Retrieved Knowledge:
{context}
"""

GREETING_SYSTEM = """You are a helpful assistant for a hospital Building Services \
Maintenance (BSM) engineering knowledge system. Respond naturally to greetings \
and general questions. Let the user know you can answer technical BSM questions \
about mechanical, electrical, fire protection, plumbing and drainage standards."""


def render() -> None:
    mode_header(
        icon="🚀",
        title="Mode 4 · Hybrid RAG",
        description="Vector search (FAISS) + Graph search (Neo4j) fused for maximum recall.",
    )

    for key in [CTX_LOG_KEY, METRICS_KEY]:
        if key not in st.session_state:
            st.session_state[key] = []

    t_chat, t_ctx, t_metrics = st.tabs(["💬 Chat", "🔍 Retrieved Knowledge", "📈 Metrics"])

    with t_chat:
        render_history(HISTORY_KEY)

        if prompt := st.chat_input("Ask engineering questions…"):
            st.session_state[HISTORY_KEY].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        if not is_bsm_relevant(prompt):
                            answer = stream_llm(GREETING_SYSTEM, prompt)
                            st.session_state[HISTORY_KEY].append(
                                {"role": "assistant", "content": answer}
                            )
                            log_answer(METRICS_KEY, prompt, answer, "")
                        else:
                            with st.spinner("Retrieving vector + graph knowledge…"):
                                result = retrieve_hybrid_context(
                                    query=prompt,
                                    graph_function=retrieve_graph_context,
                                    top_k=10,
                                )

                            if result.get("vector", "").strip() or result.get("graph", "").strip():
                                st.session_state[CTX_LOG_KEY].append({
                                    "question": prompt,
                                    "vector":   result.get("vector", ""),
                                    "graph":    result.get("graph",  ""),
                                })

                            answer = stream_llm(
                                SYSTEM_TEMPLATE.format(context=result.get("combined", "")), prompt
                            )
                            st.session_state[HISTORY_KEY].append(
                                {"role": "assistant", "content": answer}
                            )
                            log_answer(METRICS_KEY, prompt, answer, result.get("combined", ""))

                    except Exception as e:
                        st.error(f"Hybrid RAG error: {e}")

    with t_ctx:
        st.subheader("Retrieved Knowledge")
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
                    col_v, col_g = st.columns(2)
                    with col_v:
                        st.markdown("**📌 Vector Retrieval**")
                        context_panel(f"VECTOR · Q{q_num}", entry["vector"])
                    with col_g:
                        st.markdown("**🕸️ Graph Retrieval**")
                        context_panel(f"GRAPH · Q{q_num}", entry["graph"])

    with t_metrics:
        render_metrics_tab(METRICS_KEY)