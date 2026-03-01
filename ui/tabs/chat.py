from typing import Any

import streamlit as st

from ui.api import ApiClient
from ui.exceptions import ApiClientError
from ui.utils import (
    format_message_metadata,
    get_chat_history,
    merge_stream_chunk,
    provider_label,
    session_label,
    show_result,
    source_label,
    tool_label,
)


def load_session_messages(client: ApiClient, session_id: int) -> None:
    """Load session messages into Streamlit state.

    Args:
        client: UI API client.
        session_id: Session ID.

    """
    messages = client.list_messages(session_id=session_id)
    if messages.ok and isinstance(messages.data, list):
        st.session_state["chat_history"][str(session_id)] = [
            {
                "role": str(item.get("role", "")),
                "content": str(item.get("content", "")),
                "provider_id": item.get("provider_id"),
                "model_name": item.get("model_name"),
                "tool_ids": item.get("tool_ids") or [],
            }
            for item in messages.data
        ]


def get_provider_context(
    client: ApiClient,
) -> tuple[int, str] | None:
    """Resolve provider and model selection for chat.

    Args:
        client: UI API client.

    Returns:
        Selected provider ID and model name, or None when unavailable.

    """
    providers_result = client.list_providers()
    if not (providers_result.ok and isinstance(providers_result.data, list)):
        show_result(providers_result)
        return None

    providers = providers_result.data
    providers_map = {
        provider["id"]: provider
        for provider in providers
        if isinstance(provider, dict) and provider.get("id")
    }
    provider_ids = sorted(providers_map.keys())
    if not provider_ids:
        st.warning("Create provider first")
        return None

    default_provider_id = st.session_state["selected_provider_id"]
    if default_provider_id not in provider_ids:
        default_provider_id = provider_ids[0]
        st.session_state["selected_provider_id"] = default_provider_id

    selected_provider_id = st.selectbox(
        "Provider",
        options=provider_ids,
        index=provider_ids.index(default_provider_id),
        format_func=lambda provider_id: provider_label(providers_map[provider_id]),
        key="chat_provider_selector",
    )
    st.session_state["selected_provider_id"] = selected_provider_id

    models_result = client.provider_models(provider_id=selected_provider_id)
    if not (models_result.ok and isinstance(models_result.data, list)):
        show_result(models_result)
        return None

    model_names = [
        str(item.get("name", ""))
        for item in models_result.data
        if isinstance(item, dict) and item.get("name")
    ]
    if not model_names:
        st.warning("No models available for selected provider")
        return None

    default_model = st.session_state["selected_model_name"]
    if default_model not in model_names:
        default_model = model_names[0]
        st.session_state["selected_model_name"] = default_model

    selected_model_name = st.selectbox(
        "Model",
        options=model_names,
        index=model_names.index(default_model),
        key="chat_model_selector",
    )
    st.session_state["selected_model_name"] = selected_model_name
    return selected_provider_id, selected_model_name


def get_tool_context(
    client: ApiClient,
) -> tuple[list[str], dict[str, dict[str, Any]], list[str]] | None:
    """Resolve available tools and default tool selection.

    Args:
        client: UI API client.

    Returns:
        Tool IDs, tool metadata map, and default selected tool IDs.

    """
    tools_result = client.list_tools()
    if not (tools_result.ok and isinstance(tools_result.data, list)):
        show_result(tools_result)
        return None

    tools = [
        item for item in tools_result.data if isinstance(item, dict) and item.get("id")
    ]
    tools_map = {str(tool["id"]): tool for tool in tools}
    tool_ids = sorted(tools_map.keys())
    default_tool_ids: list[str] = []
    return tool_ids, tools_map, default_tool_ids


def get_completed_sources(
    client: ApiClient,
) -> tuple[list[int], dict[int, dict[str, Any]]] | None:
    """Load completed sources available for chat sessions.

    Args:
        client: UI API client.

    Returns:
        Completed source IDs and a map by source ID, or None on failure.

    """
    sources_result = client.list_sources()
    if not (sources_result.ok and isinstance(sources_result.data, list)):
        show_result(sources_result)
        return None

    completed_sources = [
        source
        for source in sources_result.data
        if isinstance(source, dict) and source.get("status") == "completed"
    ]
    completed_map = {
        source["id"]: source for source in completed_sources if source.get("id")
    }
    completed_ids = sorted(completed_map.keys())
    return completed_ids, completed_map


def get_sessions_context(client: ApiClient) -> dict[int, dict[str, Any]] | None:
    """Load sessions mapped by session ID.

    Args:
        client: UI API client.

    Returns:
        Session map keyed by ID, or None on failure.

    """
    sessions_result = client.list_sessions()
    if not (sessions_result.ok and isinstance(sessions_result.data, list)):
        show_result(sessions_result)
        return None

    return {
        item["id"]: item
        for item in sessions_result.data
        if isinstance(item, dict) and item.get("id")
    }


def select_session(client: ApiClient, sessions_map: dict[int, dict[str, Any]]) -> None:
    """Render session selector and synchronize session state.

    Args:
        client: UI API client.
        sessions_map: Sessions keyed by ID.

    """
    session_options: list[int | None] = [None] + sorted(
        sessions_map.keys(), reverse=True
    )

    current_session_id = st.session_state["selected_session_id"]
    if current_session_id not in sessions_map:
        current_session_id = None
        st.session_state["selected_session_id"] = None

    selected_session_id = st.selectbox(
        "Session",
        options=session_options,
        index=session_options.index(current_session_id),
        format_func=lambda item: session_label(item, sessions_map),
        key="chat_session_selector",
    )
    if selected_session_id == st.session_state["selected_session_id"]:
        return

    st.session_state["selected_session_id"] = selected_session_id
    if selected_session_id is None:
        st.session_state["selected_session_source_ids"] = []
        return

    session_sources = sessions_map[selected_session_id].get("source_ids", [])
    st.session_state["selected_session_source_ids"] = list(session_sources)
    load_session_messages(client=client, session_id=selected_session_id)


def handle_new_chat(client: ApiClient) -> None:
    """Create a new chat session.

    Args:
        client: UI API client.

    """
    create_result = client.create_session(
        source_ids=st.session_state["selected_session_source_ids"]
    )
    if not (create_result.ok and isinstance(create_result.data, dict)):
        show_result(create_result)
        return

    new_session_id = int(create_result.data["id"])
    st.session_state["selected_session_id"] = new_session_id
    st.session_state["selected_session_source_ids"] = list(
        create_result.data.get("source_ids", [])
    )
    st.session_state["chat_history"][str(new_session_id)] = []
    st.rerun()


def sync_session_sources(
    client: ApiClient,
    completed_ids: list[int],
    completed_map: dict[int, dict[str, Any]],
) -> None:
    """Synchronize selected sources with the active session.

    Args:
        client: UI API client.
        completed_ids: IDs of completed sources.
        completed_map: Completed sources keyed by ID.

    """
    selected_sources = st.multiselect(
        "Sources for current chat session",
        options=completed_ids,
        default=[
            source_id
            for source_id in st.session_state["selected_session_source_ids"]
            if source_id in completed_map
        ],
        format_func=lambda source_id: source_label(completed_map[source_id]),
        key="chat_sources_selector",
    )

    if selected_sources == st.session_state["selected_session_source_ids"]:
        return

    selected_session_id = st.session_state["selected_session_id"]
    if selected_session_id is None:
        st.session_state["selected_session_source_ids"] = selected_sources
        return

    update_result = client.update_session(
        session_id=int(selected_session_id),
        source_ids=selected_sources,
    )
    if update_result.ok:
        st.session_state["selected_session_source_ids"] = selected_sources
        return

    show_result(update_result)
    st.session_state["chat_sources_selector"] = st.session_state[
        "selected_session_source_ids"
    ]
    st.rerun()


def render_history(client: ApiClient, session_id: int | None) -> list[dict[str, Any]]:
    """Render chat history for the selected session.

    Args:
        client: UI API client.
        session_id: Selected session ID, or None.

    Returns:
        Mutable chat history list for the current session.

    """
    if session_id is None:
        st.info("Session will be created automatically on first message")
        return []

    if str(session_id) not in st.session_state["chat_history"]:
        load_session_messages(client=client, session_id=int(session_id))

    history = get_chat_history(int(session_id))
    for message in history:
        role = "assistant" if message.get("role") == "agent" else "user"
        with st.chat_message(role):
            st.markdown(message.get("content", ""))
            metadata_text = format_message_metadata(message)
            if metadata_text:
                st.caption(metadata_text)

    return history


def ensure_session_for_prompt(client: ApiClient) -> int | None:
    """Ensure an active session exists before sending a prompt.

    Args:
        client: UI API client.

    Returns:
        Existing or newly created session ID, or None on failure.

    """
    session_id = st.session_state["selected_session_id"]
    if session_id is not None:
        return int(session_id)

    create_result = client.create_session(
        source_ids=st.session_state["selected_session_source_ids"]
    )
    if not (create_result.ok and isinstance(create_result.data, dict)):
        show_result(create_result)
        return None

    new_session_id = int(create_result.data["id"])
    st.session_state["selected_session_id"] = new_session_id
    st.session_state["chat_history"][str(new_session_id)] = []
    return new_session_id


def build_chat_tools_payload(
    selected_tool_ids: list[str], selected_source_ids: list[int]
) -> list[dict[str, Any]] | None:
    """Build chat tools payload for the API request."""
    payload: list[dict[str, Any]] = []
    for tool_id in selected_tool_ids:
        if tool_id == "retrieve":
            if not selected_source_ids:
                st.error("Retrieve tool requires at least one source in the session")
                return None
            payload.append({"id": tool_id, "source_ids": list(selected_source_ids)})
            continue

        payload.append({"id": tool_id})

    return payload


def select_chat_tools(
    tool_ids: list[str],
    tools_map: dict[str, dict[str, Any]],
) -> list[str]:
    """Render tool selector and apply source-aware defaults."""
    if "chat_tools_selector" not in st.session_state:
        st.session_state["chat_tools_selector"] = [
            tool_id
            for tool_id in st.session_state["selected_tool_ids"]
            if tool_id in tools_map
        ]
    else:
        st.session_state["chat_tools_selector"] = [
            tool_id
            for tool_id in st.session_state["chat_tools_selector"]
            if tool_id in tools_map
        ]

    return st.multiselect(
        "Tools for this request",
        options=tool_ids,
        format_func=lambda tool_id: tool_label(tools_map[tool_id]),
        key="chat_tools_selector",
    )


def sync_retrieve_tool_with_sources(tools_map: dict[str, dict[str, Any]]) -> None:
    """Ensure retrieve is selected when sources are selected."""
    if (
        not st.session_state["selected_session_source_ids"]
        or "retrieve" not in tools_map
    ):
        return

    if "retrieve" not in st.session_state["selected_tool_ids"]:
        st.session_state["selected_tool_ids"] = [
            *st.session_state["selected_tool_ids"],
            "retrieve",
        ]

    if (
        "chat_tools_selector" in st.session_state
        and "retrieve" not in st.session_state["chat_tools_selector"]
    ):
        st.session_state["chat_tools_selector"] = [
            *st.session_state["chat_tools_selector"],
            "retrieve",
        ]


def send_prompt(
    client: ApiClient,
    prompt: str,
    session_id: int,
    provider_id: int,
    model_name: str,
    tool_ids: list[str],
    tools_payload: list[dict[str, Any]],
) -> None:
    """Send a prompt and stream assistant response.

    Args:
        client: UI API client.
        prompt: User prompt text.
        session_id: Active session ID.
        provider_id: Selected provider ID.
        model_name: Selected model name.
        tool_ids: Selected tool IDs.
        tools_payload: Tools payload for backend request.

    """
    history = get_chat_history(session_id)
    history.append(
        {
            "role": "user",
            "content": prompt,
            "provider_id": provider_id,
            "model_name": model_name,
            "tool_ids": list(tool_ids),
        }
    )
    with st.chat_message("user"):
        st.markdown(prompt)
        metadata_text = format_message_metadata(history[-1])
        if metadata_text:
            st.caption(metadata_text)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        metadata_placeholder = st.empty()
        final_answer = ""
        chunk_model_name = model_name
        chunk_tool_ids = list(tool_ids)
        try:
            for chunk in client.stream_chat(
                session_id=session_id,
                message=prompt,
                provider_id=provider_id,
                model_name=model_name,
                tools=tools_payload,
            ):
                role = str(chunk.get("role", ""))
                content = str(chunk.get("content", ""))
                model_name_from_chunk = str(chunk.get("model_name", "")) or model_name
                tool_ids_from_chunk = chunk.get("tool_ids") or tool_ids
                if role == "agent":
                    final_answer = merge_stream_chunk(final_answer, content)
                    placeholder.markdown(final_answer)
                    chunk_model_name = model_name_from_chunk
                    chunk_tool_ids = [str(tool_id) for tool_id in tool_ids_from_chunk]
                    metadata_placeholder.caption(
                        format_message_metadata(
                            {
                                "model_name": chunk_model_name,
                                "tool_ids": chunk_tool_ids,
                            }
                        )
                    )
        except ApiClientError as exc:
            st.error(f"HTTP {exc.status_code}: {exc.detail}")
            return

    if final_answer:
        history.append(
            {
                "role": "agent",
                "content": final_answer,
                "provider_id": provider_id,
                "model_name": chunk_model_name,
                "tool_ids": chunk_tool_ids,
            }
        )


def render_chat_tab(client: ApiClient) -> None:
    """Render the Chat tab.

    Args:
        client: UI API client.

    """
    st.subheader("Chat")

    provider_context = get_provider_context(client=client)
    if provider_context is None:
        return
    selected_provider_id, selected_model_name = provider_context

    sources_context = get_completed_sources(client=client)
    if sources_context is None:
        return
    completed_ids, completed_map = sources_context

    sessions_map = get_sessions_context(client=client)
    if sessions_map is None:
        return

    select_session(client=client, sessions_map=sessions_map)
    if st.button("New chat", key="new_chat_button"):
        handle_new_chat(client=client)

    sync_session_sources(
        client=client,
        completed_ids=completed_ids,
        completed_map=completed_map,
    )

    tools_context = get_tool_context(client=client)
    if tools_context is None:
        return
    tool_ids, tools_map, default_tool_ids = tools_context
    if not st.session_state["selected_tool_ids"]:
        st.session_state["selected_tool_ids"] = default_tool_ids
    sync_retrieve_tool_with_sources(tools_map=tools_map)

    selected_tool_ids = select_chat_tools(tool_ids=tool_ids, tools_map=tools_map)
    st.session_state["selected_tool_ids"] = selected_tool_ids

    current_session_id = st.session_state["selected_session_id"]
    render_history(client=client, session_id=current_session_id)

    prompt = st.chat_input("Write a message")
    if prompt:
        tools_payload = build_chat_tools_payload(
            selected_tool_ids=selected_tool_ids,
            selected_source_ids=st.session_state["selected_session_source_ids"],
        )
        if tools_payload is None:
            return

        active_session_id = ensure_session_for_prompt(client=client)
        if active_session_id is None:
            return

        send_prompt(
            client=client,
            prompt=prompt,
            session_id=active_session_id,
            provider_id=selected_provider_id,
            model_name=selected_model_name,
            tool_ids=selected_tool_ids,
            tools_payload=tools_payload,
        )
