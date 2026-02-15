from typing import Any

import streamlit as st


def init_state() -> None:
    """Initialize Streamlit state keys used by the UI."""
    defaults: dict[str, object] = {
        "selected_session_id": None,
        "selected_provider_id": None,
        "selected_model_name": "",
        "selected_tool_ids": [],
        "selected_session_source_ids": [],
        "chat_history": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_chat_history(session_id: int) -> list[dict[str, Any]]:
    history = st.session_state["chat_history"]
    return history.setdefault(str(session_id), [])
