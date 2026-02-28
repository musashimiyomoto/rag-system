from typing import Any

import streamlit as st

from ui.models import ApiResult


def show_result(result: ApiResult, success_message: str | None = None) -> None:
    """Render API result as success output or formatted error.

    Args:
        result: API call result wrapper.
        success_message: Optional success message shown when call succeeds.

    """
    if result.ok:
        if success_message:
            st.success(success_message)
        if result.data is not None:
            st.json(result.data)
        return

    detail = format_error_detail(result.detail)
    st.error(f"HTTP {result.status_code}: {detail}")


def show_table(data: list[dict[str, Any]], title: str | None = None) -> None:
    """Render a data table.

    Args:
        data: Table rows as dictionaries.
        title: Optional section title.

    """
    if title:
        st.subheader(title)
    if not data:
        st.info("No data")
        return
    st.dataframe(data, width="stretch")


def format_error_detail(detail: str | None) -> str:
    """Normalize error detail text for UI display.

    Args:
        detail: Raw error detail from API response.

    Returns:
        User-facing error detail text.

    """
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
    """Build a display label for a source.

    Args:
        source: Source record payload.

    Returns:
        Source label text.

    """
    source_id = source["id"]
    source_name = source.get("name", "unknown")
    source_status = source.get("status", "unknown")
    return f"{source_id} - {source_name} ({source_status})"


def provider_label(provider: dict[str, Any]) -> str:
    """Build a display label for a provider.

    Args:
        provider: Provider record payload.

    Returns:
        Provider label text.

    """
    provider_id = provider["id"]
    provider_name = provider.get("name", "unknown")
    status = "active" if provider.get("is_active") else "inactive"
    return f"{provider_id} - {provider_name} [{status}]"


def tool_label(tool: dict[str, Any]) -> str:
    """Build a display label for a tool.

    Args:
        tool: Tool record payload.

    Returns:
        Tool label text.

    """
    tool_id = str(tool.get("id", "unknown"))
    tool_title = str(tool.get("title", tool_id))
    return f"{tool_title} ({tool_id})"


def session_label(
    session_item: int | None, sessions_map: dict[int, dict[str, Any]]
) -> str:
    """Build a display label for a session selector option.

    Args:
        session_item: Session ID or None option.
        sessions_map: Sessions keyed by ID.

    Returns:
        Session label text.

    """
    if session_item is None:
        return "No active session"
    source_ids = sessions_map.get(session_item, {}).get("source_ids", [])
    return f"Session #{session_item} ({len(source_ids)} sources)"


def merge_stream_chunk(current_text: str, chunk_text: str) -> str:
    """Merge a streamed chunk into current assistant text.

    Args:
        current_text: Already rendered assistant text.
        chunk_text: Newly received chunk text.

    Returns:
        Updated assistant text.

    """
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
    """Format message metadata shown under chat messages.

    Args:
        message: Chat message payload.

    Returns:
        Formatted metadata string or empty string.

    """
    model_name = str(message.get("model_name") or "")
    tool_ids = message.get("tool_ids") or []
    if not model_name and not tool_ids:
        return ""
    tools_text = ", ".join(str(tool_id) for tool_id in tool_ids) if tool_ids else "-"
    model_text = model_name or "-"
    return f"`model: {model_text} | tools: {tools_text}`"


def init_state() -> None:
    """Initialize default Streamlit state used by UI tabs."""
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
    """Get mutable chat history for a session.

    Args:
        session_id: Session ID.

    Returns:
        Mutable list of chat message dictionaries.

    """
    history = st.session_state["chat_history"]
    return history.setdefault(str(session_id), [])
