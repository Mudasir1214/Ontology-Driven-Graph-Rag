"""
components/ui.py  –  Reusable UI building blocks.
"""
import streamlit as st
from openai import APIConnectionError, APIStatusError
from config import get_llm_client, LLM_MODEL


# ── Mode header ──────────────────────────────────────────────────────────────

def mode_header(icon: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="mode-bar">
            <span class="mode-icon">{icon}</span>
            <div>
                <h1 style="margin:0;padding:0;">{title}</h1>
                <span class="mode-desc">{description}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Standard chat history renderer ──────────────────────────────────────────

def render_history(history_key: str) -> None:
    """Render all messages stored under *history_key* in session state."""
    for msg in st.session_state.get(history_key, []):
        st.chat_message(msg["role"]).write(msg["content"])


# ── LLM streaming call ───────────────────────────────────────────────────────

def stream_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call the LLM with a system + user message and stream the response
    directly into the Streamlit chat widget.  Returns the full text.

    A fresh client is created on every call (see config.get_llm_client) so
    stale HTTP connections never cause "Connection error" on repeated queries.
    The openai SDK's built-in max_retries=2 handles transient blips silently.
    """
    try:
        client = get_llm_client()
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            stream=True,
        )
        return st.write_stream(stream)

    except APIConnectionError as e:
        msg = (
            "⚠️ Could not reach the DeepSeek API. "
            "Check your internet connection or VPN and try again.\n\n"
            f"Detail: {e}"
        )
        st.error(msg)
        return msg

    except APIStatusError as e:
        msg = (
            f"⚠️ DeepSeek API returned an error (HTTP {e.status_code}). "
            "This may be a rate-limit or server issue — wait a moment and retry.\n\n"
            f"Detail: {e.message}"
        )
        st.error(msg)
        return msg


# ── Context panel (shown beside or below chat) ───────────────────────────────

def context_panel(label: str, content: str) -> None:
    """Render a titled code block for retrieved context."""
    st.markdown(f'<span class="ctx-badge">{label}</span>', unsafe_allow_html=True)
    st.code(content or "— no context retrieved —", language="text")