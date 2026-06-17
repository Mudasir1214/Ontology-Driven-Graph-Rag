"""
modes/mode_vector.py  –  Mode 2: Vector Embedding RAG
"""
import streamlit as st
from components.ui import mode_header, render_history, stream_llm, context_panel
from components.metrics import render_metrics_tab, log_answer
from vector_rag import retrieve_vector_context, retrieve_vector_chunks
from relevance_check import is_bsm_relevant

HISTORY_KEY = "history_vector"
CTX_LOG_KEY = "ctx_log_vector"
METRICS_KEY = "metrics_vector"

SYSTEM_TEMPLATE = """You are an engineering standards expert for hospital BSM.
Answer based on the retrieved context below.

Rules:
1. Cite chapter IDs and document names when available.
2. Quote numerical requirements exactly as stated.
3. If multiple chapters mention the topic, compare them — especially if they
   describe different editions or years of the same standard.
4. REASON from the context: if the context describes what a standard DOES contain,
   you can infer what it does NOT contain. For example, if the 2012 edition lists
   specific standards and BS 8491 is not among them, you can state it is not mentioned.
5. Only say "No information found" if the context has absolutely no relevant content
   and you cannot draw any reasonable inference from it.

Context:
{context}
"""

GREETING_SYSTEM = """You are a helpful assistant for a hospital Building Services \
Maintenance (BSM) engineering knowledge system. Respond naturally to greetings \
and general questions. Let the user know you can answer technical BSM questions \
about mechanical, electrical, fire protection, plumbing and drainage standards."""


def render() -> None:
    mode_header(
        icon="📌",
        title="Mode 2 · Vector RAG",
        description="Sentence embeddings + FAISS semantic similarity search.",
    )

    for key in [CTX_LOG_KEY, METRICS_KEY]:
        if key not in st.session_state:
            st.session_state[key] = []

    t_chat, t_ctx, t_metrics = st.tabs(["💬 Chat", "📚 Retrieved Chunks", "📈 Metrics"])

    with t_chat:
        render_history(HISTORY_KEY)

        if prompt := st.chat_input("Ask a question..."):
            st.session_state[HISTORY_KEY].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        # LLM classifier decides before any retrieval runs
                        if not is_bsm_relevant(prompt):
                            answer = stream_llm(GREETING_SYSTEM, prompt)
                            st.session_state[HISTORY_KEY].append(
                                {"role": "assistant", "content": answer}
                            )
                            log_answer(METRICS_KEY, prompt, answer, "")
                        else:
                            with st.spinner("Searching vector store..."):
                                scored_chunks = retrieve_vector_chunks(prompt, top_k=5)
                                context       = retrieve_vector_context(prompt, top_k=5)

                            if scored_chunks:
                                st.session_state[CTX_LOG_KEY].append({
                                    "question": prompt,
                                    "chunks":   scored_chunks,
                                    "context":  context,
                                })

                            answer = stream_llm(SYSTEM_TEMPLATE.format(context=context or ""), prompt)
                            st.session_state[HISTORY_KEY].append(
                                {"role": "assistant", "content": answer}
                            )
                            log_answer(METRICS_KEY, prompt, answer, context or "")

                    except Exception as e:
                        st.error(f"Vector RAG error: {e}")

    with t_ctx:
        st.subheader("Retrieved Semantic Chunks")
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
                    for chunk in entry["chunks"]:
                        score   = chunk["score"]
                        bar_pct = int(score * 100)
                        meta_parts = []
                        if chunk.get("chapter"): meta_parts.append(f"Chapter {chunk['chapter']}")
                        if chunk.get("source"):  meta_parts.append(chunk["source"])
                        if chunk.get("module"):  meta_parts.append(f"Module: {chunk['module']}")
                        meta_str = " · ".join(meta_parts) or "—"
                        st.markdown(
                            f"""<div style="display:flex;justify-content:space-between;
                                            align-items:center;margin-top:12px;margin-bottom:2px;">
                                <span style="font-size:0.78rem;color:#8B949E;">
                                    #{chunk['rank']} · {meta_str}</span>
                                <span style="font-size:0.78rem;font-weight:600;color:#22C55E;">
                                    score&nbsp;{score:.2f}</span></div>
                                <div style="background:#30363D;border-radius:4px;height:4px;margin-bottom:8px;">
                                <div style="width:{bar_pct}%;height:4px;border-radius:4px;
                                    background:#22C55E;"></div></div>""",
                            unsafe_allow_html=True,
                        )
                        context_panel(f"Chunk {chunk['rank']}", chunk["text"])

    with t_metrics:
        render_metrics_tab(METRICS_KEY)