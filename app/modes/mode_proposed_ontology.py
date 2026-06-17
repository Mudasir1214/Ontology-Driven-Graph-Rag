"""
modes/mode_proposed.py  –  Mode 5: Proposed Ontology-based RAG
"""
import streamlit as st
from proposed_ontology_rag import retrieve_proposed_context
from components.ui import mode_header, render_history, stream_llm, context_panel
from components.metrics import render_metrics_tab, log_answer
from relevance_check import is_bsm_relevant

HISTORY_KEY = "history_proposed"
CTX_LOG_KEY = "ctx_log_proposed"
METRICS_KEY = "metrics_proposed"

SYSTEM_TEMPLATE = """You are an expert hospital Building Services Maintenance (BSM) engineer \
and regulatory compliance specialist.

Answer using the retrieved knowledge below. Follow these rules strictly:

1. EDITION ATTRIBUTION IS THE MOST IMPORTANT RULE.
   Before answering any question about a specific edition or year, identify which
   edition each piece of evidence belongs to using:
   - The Document field on graph rules (includes year in parentheses)
   - The chapter IDs in supplementary text (J001=2022 edition, J002=2012 edition etc.)
   Never mix up evidence from different editions in your conclusion.

2. ANSWER STRUCTURE: Give a direct, unambiguous answer first (e.g. "No, the 2012
   edition does not mention BS 8491"), then provide the evidence breakdown.
   Avoid self-contradictory openers like "yes... but only in the 2022 edition."

3. If CROSS-STANDARD CONFLICTS are flagged, explain them clearly.

4. Cite rule IDs, chapter IDs, document names, and edition years.

5. Quote numerical values (mm, g/m², %, kV, minutes) exactly as stated.

6. If the same topic appears in multiple editions with different content, present
   each edition separately with its source citation.

7. If information is genuinely not in the retrieved knowledge, say:
   "Not found in the available knowledge base."

Retrieved Knowledge:
{context}
"""

GREETING_SYSTEM = """You are a helpful assistant for a hospital Building Services \
Maintenance (BSM) engineering knowledge system. Respond naturally to greetings \
and general questions. Let the user know you can answer technical BSM questions \
about mechanical, electrical, fire protection, plumbing and drainage standards."""


def render() -> None:
    mode_header(
        icon="🧬",
        title="Mode 5 · Proposed Ontology-based RAG",
        description="Full system: Vector (text_data) + Graph (batch ontology) + Ductile Graph.",
    )

    for key in [CTX_LOG_KEY, METRICS_KEY]:
        if key not in st.session_state:
            st.session_state[key] = []

    t_chat, t_ctx, t_conflicts, t_metrics = st.tabs([
        "💬 Chat", "🔍 Retrieved Knowledge", "⚠️ Conflicts", "📈 Metrics"
    ])

    with t_chat:
        st.info(
            "**Proposed mode** — all three knowledge sources. "
            "Cross-standard conflicts are automatically detected and flagged.",
            icon=None,
        )
        render_history(HISTORY_KEY)

        if prompt := st.chat_input("Ask any BSM engineering question…"):
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
                            with st.spinner("Retrieving from all knowledge sources…"):
                                result = retrieve_proposed_context(query=prompt, top_k=10)

                            _has_content = any([
                                result.get("vector",  "").strip(),
                                result.get("graph",   "").strip(),
                                result.get("ductile", "").strip(),
                            ])
                            if _has_content:
                                st.session_state[CTX_LOG_KEY].append({
                                    "question":  prompt,
                                    "vector":    result["vector"],
                                    "graph":     result["graph"],
                                    "ductile":   result["ductile"],
                                    "conflicts": result["conflicts"],
                                })

                            if result["conflicts"]:
                                conflict_names = [c["component"] for c in result["conflicts"]]
                                st.warning(
                                    f"⚠️ **{len(result['conflicts'])} cross-standard conflict(s) detected**\n\n"
                                    + "\n".join(f"• {n}" for n in conflict_names)
                                )

                            answer = stream_llm(
                                SYSTEM_TEMPLATE.format(context=result["combined"]), prompt
                            )
                            st.session_state[HISTORY_KEY].append(
                                {"role": "assistant", "content": answer}
                            )
                            log_answer(METRICS_KEY, prompt, answer, result["combined"])

                    except Exception as e:
                        st.error(f"Proposed RAG error: {e}")

    with t_ctx:
        st.subheader("Retrieved Knowledge — All Sources")
        log = st.session_state.get(CTX_LOG_KEY, [])
        if not log:
            st.caption("No retrieval yet — ask a BSM question in the Chat tab.")
        else:
            for i, entry in enumerate(reversed(log)):
                q_num = len(log) - i
                with st.expander(
                    f"Q{q_num}: {entry['question'][:80]}"
                    f"{'…' if len(entry['question']) > 80 else ''}",
                    expanded=(i == 0),
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**📌 Vector (text_data)**")
                        context_panel(f"VECTOR · Q{q_num}", entry["vector"] or "*(no vector results)*")
                    with col2:
                        st.markdown("**🕸️ Graph (batch ontology)**")
                        context_panel(f"GRAPH · Q{q_num}", entry["graph"] or "*(no graph results)*")
                    with col3:
                        st.markdown("**🔩 Ductile Graph**")
                        context_panel(f"DUCTILE · Q{q_num}", entry["ductile"] or "*(no ductile results)*")

    with t_conflicts:
        st.subheader("Cross-Standard Conflict Detection")
        st.caption(
            "Conflicts detected when the same component appears in multiple "
            "standards with contradictory requirements."
        )
        log = st.session_state.get(CTX_LOG_KEY, [])
        all_conflicts = []
        for entry in log:
            for c in entry.get("conflicts", []):
                c_with_q = {**c, "_question": entry["question"]}
                if c_with_q not in all_conflicts:
                    all_conflicts.append(c_with_q)

        if not all_conflicts:
            st.info("No conflicts detected yet. Ask about ductile iron pipe coating requirements.")
        else:
            st.success(f"**{len(all_conflicts)} unique conflict(s) detected** across this session.")
            for c in all_conflicts:
                st.markdown(
                    f"""<div style="border:1px solid #30363D;border-left:4px solid #E24B4A;
                        border-radius:8px;padding:12px 16px;margin-bottom:12px;">
                        <div style="font-weight:500;margin-bottom:8px;">⚠️ {c['component']}</div>
                        <div style="font-size:0.82rem;color:#8B949E;margin-bottom:4px;">
                        Triggered by: <em>{c['_question'][:60]}</em></div>
                        <table style="width:100%;font-size:0.82rem;border-collapse:collapse;">
                        <tr><td style="padding:4px 8px;font-weight:500;color:#8B949E;width:40%;">
                        {c['standard_a']}</td><td style="padding:4px 8px;">{c['requirement_a']}</td></tr>
                        <tr style="background:#161B22;"><td style="padding:4px 8px;font-weight:500;color:#8B949E;">
                        {c['standard_b']}</td><td style="padding:4px 8px;">{c['requirement_b']}</td></tr>
                        </table></div>""",
                    unsafe_allow_html=True,
                )

    with t_metrics:
        render_metrics_tab(METRICS_KEY)