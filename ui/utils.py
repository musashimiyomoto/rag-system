from typing import Any

import streamlit as st

from ui.models import ApiResult


def show_result(result: ApiResult, success_message: str | None = None) -> None:
    """Render an API call result as success payload or formatted error."""
    if result.ok:
        if success_message:
            st.success(success_message)
        if result.data is not None:
            st.json(result.data)
        return

    detail = format_error_detail(result.detail)
    st.error(f"HTTP {result.status_code}: {detail}")


def show_table(data: list[dict[str, Any]], title: str | None = None) -> None:
    """Render a table with optional title and empty-state message."""
    if title:
        st.subheader(title)
    if not data:
        st.info("No data")
        return
    st.dataframe(data, use_container_width=True)


def format_error_detail(detail: str | None) -> str:
    """Normalize API error detail text for user-facing output."""
    if not detail:
        return "Unknown error"

    known_conflicts = [
        "Source is used by one or more sessions",
        "Source is not completed",
        "Provider is inactive",
        "Session not found",
    ]
    for text in known_conflicts:
        if text.lower() in detail.lower():
            return detail
    return detail


def source_label(source: dict[str, Any]) -> str:
    """Build a display label for a source record."""
    source_id = source["id"]
    source_name = source.get("name", "unknown")
    source_status = source.get("status", "unknown")
    return f"{source_id} - {source_name} ({source_status})"


def provider_label(provider: dict[str, Any]) -> str:
    """Build a display label for a provider record."""
    provider_id = provider["id"]
    provider_name = provider.get("name", "unknown")
    status = "active" if provider.get("is_active") else "inactive"
    return f"{provider_id} - {provider_name} [{status}]"


def tool_label(tool: dict[str, Any]) -> str:
    """Build a display label for a tool record."""
    tool_id = str(tool.get("id", "unknown"))
    tool_title = str(tool.get("title", tool_id))
    return f"{tool_title} ({tool_id})"


def session_label(
    session_item: int | None, sessions_map: dict[int, dict[str, Any]]
) -> str:
    """Build a display label for a session selector option."""
    if session_item is None:
        return "No active session"
    source_ids = sessions_map.get(session_item, {}).get("source_ids", [])
    return f"Session #{session_item} ({len(source_ids)} sources)"


def merge_stream_chunk(current_text: str, chunk_text: str) -> str:
    """Merge streaming text chunk into already rendered content."""
    if not chunk_text:
        return current_text
    if chunk_text == current_text:
        return current_text
    if chunk_text.startswith(current_text):
        return chunk_text
    if current_text.endswith(chunk_text):
        return current_text
    return current_text + chunk_text


def format_message_metadata(message: dict[str, Any]) -> str:
    """Format model/tool metadata shown under chat messages."""
    model_name = str(message.get("model_name") or "")
    tool_ids = message.get("tool_ids") or []
    if not model_name and not tool_ids:
        return ""
    tools_text = ", ".join(str(tool_id) for tool_id in tool_ids) if tool_ids else "-"
    model_text = model_name or "-"
    return f"`model: {model_text} | tools: {tools_text}`"


def init_state() -> None:
    """Initialize Streamlit state keys required by UI tabs."""
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
    """Return mutable chat history list for a given session."""
    history = st.session_state["chat_history"]
    return history.setdefault(str(session_id), [])
