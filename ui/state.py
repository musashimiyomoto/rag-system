import streamlit as st


def init_state() -> None:
    """Initialize Streamlit state keys used by the UI."""
    defaults: dict[str, object] = {
        "api_base_url": "http://api:5000",
        "selected_session_id": 1,
        "selected_source_id": 1,
        "selected_provider_id": 1,
        "selected_model_name": "",
        "chat_history": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_chat_history(session_id: int) -> list[dict[str, str]]:
    history = st.session_state["chat_history"]
    return history.setdefault(str(session_id), [])
