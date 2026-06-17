"""
components/metrics.py  –  Per-session retrieval & answer quality metrics panel.

Computes and displays:
  • Token-overlap F1 / Precision / Recall  (answer vs ground-truth)
  • Faithfulness score  (answer tokens found in retrieved context)
  • Per-question results table
  • Session aggregate bar chart

Usage in any mode:
    from components.metrics import render_metrics_tab, log_answer

    # After generating an answer:
    log_answer(METRICS_KEY, question, answer, context)

    # In the metrics tab:
    with t_metrics:
        render_metrics_tab(METRICS_KEY)
"""
from __future__ import annotations

import re
import streamlit as st
import pandas as pd


# ---------------------------------------------------------------------------
# Token-level helpers
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _token_f1(prediction: str, reference: str) -> tuple[float, float, float]:
    """
    Compute token-overlap Precision, Recall, F1 between two strings.
    Identical to the SQuAD evaluation metric — standard for QA papers.

    Returns (precision, recall, f1) each in [0, 1].
    """
    pred_tokens = _tokenise(prediction)
    ref_tokens  = _tokenise(reference)

    if not pred_tokens or not ref_tokens:
        return 0.0, 0.0, 0.0

    pred_set = set(pred_tokens)
    ref_set  = set(ref_tokens)
    common   = pred_set & ref_set

    if not common:
        return 0.0, 0.0, 0.0

    precision = len(common) / len(pred_set)
    recall    = len(common) / len(ref_set)
    f1        = 2 * precision * recall / (precision + recall)
    return round(precision, 3), round(recall, 3), round(f1, 3)


def _faithfulness(answer: str, context: str) -> float:
    """
    Faithfulness = fraction of answer tokens that appear in the retrieved context.
    A high score means the answer is grounded in the retrieved evidence.
    A score near 0 suggests hallucination.
    """
    answer_tokens  = set(_tokenise(answer))
    context_tokens = set(_tokenise(context))

    if not answer_tokens:
        return 0.0

    overlap = answer_tokens & context_tokens
    return round(len(overlap) / len(answer_tokens), 3)


# ---------------------------------------------------------------------------
# Session-state log
# ---------------------------------------------------------------------------

def log_answer(
    metrics_key: str,
    question:    str,
    answer:      str,
    context:     str,
    reference:   str = "",
) -> None:
    """
    Append one QA turn to the metrics log stored under *metrics_key*.

    Parameters
    ----------
    metrics_key : session-state key unique to this mode (e.g. "metrics_vector")
    question    : the user's query
    answer      : the LLM-generated answer
    context     : the full retrieved context string (used for faithfulness)
    reference   : optional ground-truth answer; enables F1/P/R computation
    """
    if metrics_key not in st.session_state:
        st.session_state[metrics_key] = []

    faith = _faithfulness(answer, context)

    if reference.strip():
        prec, rec, f1 = _token_f1(answer, reference)
    else:
        prec = rec = f1 = None   # can't compute without ground-truth

    st.session_state[metrics_key].append({
        "Q#":          len(st.session_state[metrics_key]) + 1,
        "Question":    question[:60] + ("…" if len(question) > 60 else ""),
        "Faithfulness":faith,
        "Precision":   prec,
        "Recall":      rec,
        "F1":          f1,
        "_answer":     answer,    # hidden — for future export
        "_context":    context,
    })


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_metrics_tab(metrics_key: str) -> None:
    """
    Render the full metrics panel inside whichever tab the caller places it in.
    """
    log = st.session_state.get(metrics_key, [])

    st.subheader("Answer Quality Metrics")
    st.caption(
        "**Faithfulness** — fraction of answer tokens grounded in the retrieved context "
        "(1.0 = fully grounded, 0.0 = potential hallucination).  "
        "**F1 / Precision / Recall** — token overlap vs your reference answer "
        "(only shown when you provide a reference below)."
    )

    # ── Optional ground-truth input ──────────────────────────────────────────
    with st.expander("➕ Add reference answer for latest question (enables F1)", expanded=False):
        ref_input = st.text_area(
            "Paste the correct / expected answer:",
            height=80,
            key=f"{metrics_key}_ref_input",
        )
        if st.button("Compute F1", key=f"{metrics_key}_f1_btn"):
            if log and ref_input.strip():
                last = log[-1]
                p, r, f = _token_f1(last["_answer"], ref_input)
                last["Precision"] = p
                last["Recall"]    = r
                last["F1"]        = f
                st.success(f"F1 = {f:.3f}  |  Precision = {p:.3f}  |  Recall = {r:.3f}")
            else:
                st.warning("Ask at least one question first, and paste a reference answer.")

    if not log:
        st.info("No data yet — ask questions in the Chat tab to populate this panel.")
        return

    # ── Build display DataFrame ───────────────────────────────────────────────
    display_cols = ["Q#", "Question", "Faithfulness", "Precision", "Recall", "F1"]
    df = pd.DataFrame(log)[display_cols].copy()

    # NOTE: st.dataframe renders via a canvas-based grid (glide-data-grid).
    # Canvas pixels cannot respond to CSS variables or theme changes —
    # whatever colour is baked in at Python level is permanent regardless
    # of which theme the user later switches to. Rendering as a plain HTML
    # table instead means every cell is real DOM, so it inherits the
    # --bg-surface / --text-primary CSS variables and switches with the
    # theme toggle automatically, just like the rest of the app.

    def _faith_class(val):
        if val is None: return ""
        if val >= 0.7:  return "metric-good"
        if val >= 0.4:  return "metric-mid"
        return "metric-bad"

    def _f1_class(val):
        if val is None: return ""
        if val >= 0.6:  return "metric-good"
        if val >= 0.3:  return "metric-mid"
        return "metric-bad"

    def _fmt(v):
        return f"{v:.2f}" if v is not None else "—"

    rows_html = []
    for _, row in df.iterrows():
        rows_html.append(
            f"<tr>"
            f"<td class='mt-num'>{row['Q#']}</td>"
            f"<td class='mt-q'>{row['Question']}</td>"
            f"<td class='mt-val {_faith_class(row['Faithfulness'])}'>{_fmt(row['Faithfulness'])}</td>"
            f"<td class='mt-val'>{_fmt(row['Precision'])}</td>"
            f"<td class='mt-val'>{_fmt(row['Recall'])}</td>"
            f"<td class='mt-val {_f1_class(row['F1'])}'>{_fmt(row['F1'])}</td>"
            f"</tr>"
        )

    table_html = f"""
    <style>
        .metrics-table-wrap {{
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 16px;
        }}
        table.metrics-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 0.85rem;
            background-color: var(--bg-surface);
        }}
        table.metrics-table th {{
            background-color: var(--bg-elevated);
            color: var(--text-secondary);
            text-align: left;
            padding: 10px 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }}
        table.metrics-table td {{
            padding: 9px 14px;
            color: var(--text-primary);
            border-bottom: 1px solid var(--border);
            background-color: var(--bg-surface);
        }}
        table.metrics-table tr:last-child td {{ border-bottom: none; }}
        table.metrics-table tr:hover td {{ background-color: var(--bg-elevated); }}
        td.mt-num {{ color: var(--text-muted); width: 40px; }}
        td.mt-val {{ font-weight: 600; text-align: center; width: 90px; }}
        td.metric-good {{ color: var(--success) !important; }}
        td.metric-mid  {{ color: var(--warning) !important; }}
        td.metric-bad  {{ color: var(--danger)  !important; }}
    </style>
    <div class="metrics-table-wrap">
    <table class="metrics-table">
        <thead>
            <tr>
                <th>Q#</th><th>Question</th><th>Faithfulness</th>
                <th>Precision</th><th>Recall</th><th>F1</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Session averages ──────────────────────────────────────────────────────
    faith_vals = [r["Faithfulness"] for r in log]
    f1_vals    = [r["F1"] for r in log if r["F1"] is not None]

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Faithfulness", f"{sum(faith_vals)/len(faith_vals):.2f}")
    if f1_vals:
        col2.metric("Avg F1",        f"{sum(f1_vals)/len(f1_vals):.2f}")
        col3.metric("Questions with F1", f"{len(f1_vals)} / {len(log)}")
    else:
        col2.metric("Avg F1", "—")
        col3.caption("Add reference answers above to enable F1")

    # ── Faithfulness bar chart ────────────────────────────────────────────────
    if len(log) > 1:
        st.markdown("**Faithfulness per question**")
        chart_df = pd.DataFrame({
            "Question": [f"Q{r['Q#']}" for r in log],
            "Faithfulness": faith_vals,
        }).set_index("Question")
        st.bar_chart(chart_df, color="#22C55E")

    # ── Export ────────────────────────────────────────────────────────────────
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Export metrics CSV",
        data=csv,
        file_name=f"{metrics_key}_results.csv",
        mime="text/csv",
        key=f"{metrics_key}_dl",
    )