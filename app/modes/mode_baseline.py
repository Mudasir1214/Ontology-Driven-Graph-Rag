"""
modes/mode_baseline.py  –  Mode 1: Baseline (Pure LLM)

No retrieval — DeepSeek-V3 parametric knowledge only.
"""
import streamlit as st
from components.ui import mode_header, render_history, stream_llm
from components.metrics import render_metrics_tab, log_answer

HISTORY_KEY  = "history_pure"
LOG_KEY      = "log_baseline"     # list of {question, answer} for the answer log tab
METRICS_KEY  = "metrics_baseline"

# The system prompt explicitly forbids the model from citing specific document
# numbers or clause IDs it cannot actually know — this makes hallucination
# more visible when compared against the RAG modes in your paper.
SYSTEM_PROMPT = """You are a hospital Building Services Maintenance (BSM) expert.
Answer the user's question based on your general engineering knowledge.

Important:
- Do NOT invent specific clause numbers, document IDs, or standard references
  unless you are certain they exist.
- If you are unsure, clearly say: "I am not certain — please verify against
  the relevant standard."
- Keep answers concise and factual.
"""


def render() -> None:
    mode_header(
        icon="🤖",
        title="Mode 1 · Baseline (Pure LLM)",
        description="DeepSeek-V3 parametric knowledge only — no retrieval, no grounding.",
    )

    for key in [LOG_KEY, METRICS_KEY]:
        if key not in st.session_state:
            st.session_state[key] = []

    t_chat, t_log, t_metrics = st.tabs(["💬 Chat", "📋 Answer Log", "📈 Metrics"])

    # ── Chat tab ──────────────────────────────────────────────────────────────
    with t_chat:
        # Reminder banner — helps the evaluator remember this is the control mode
        st.info(
            "⚠️ **Control mode** — no documents retrieved. "
            "Answers are based entirely on the model's training data. "
            "Compare faithfulness scores in the Metrics tab against RAG modes.",
            icon=None,
        )

        render_history(HISTORY_KEY)

        if prompt := st.chat_input("Ask a question…"):
            st.session_state[HISTORY_KEY].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    answer = stream_llm(SYSTEM_PROMPT, prompt)

            st.session_state[HISTORY_KEY].append({"role": "assistant", "content": answer})

            # Log for the answer log tab and metrics
            st.session_state[LOG_KEY].append({
                "question": prompt,
                "answer":   answer,
            })
            # context="" because baseline has no retrieved context —
            # faithfulness will be 0.0 by definition, which is the correct
            # result to show in the paper (nothing to be faithful to).
            log_answer(METRICS_KEY, prompt, answer, context="")

    # ── Answer Log tab ────────────────────────────────────────────────────────
    with t_log:
        st.subheader("Answer Log")
        st.caption("Every question and answer from this session, for easy review and comparison.")

        log = st.session_state.get(LOG_KEY, [])
        if not log:
            st.caption("No answers yet — ask a question in the Chat tab.")
        else:
            for i, entry in enumerate(reversed(log)):
                q_num = len(log) - i
                with st.expander(
                    f"Q{q_num}: {entry['question'][:80]}{'…' if len(entry['question']) > 80 else ''}",
                    expanded=(i == 0),
                ):
                    st.markdown("**Question**")
                    st.write(entry["question"])
                    st.markdown("**Answer**")
                    st.write(entry["answer"])

    # ── Metrics tab ───────────────────────────────────────────────────────────
    with t_metrics:
        st.caption(
            "For the baseline, **Faithfulness will always be 0.0** — there is no "
            "retrieved context to be faithful to. This is the expected result and "
            "is the key contrast to show in your paper against the RAG modes. "
            "Use the F1 input below to measure answer accuracy against ground truth."
        )
        render_metrics_tab(METRICS_KEY)