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
                "thinking": item.get("thinking"),
                "web_search": item.get("web_search"),
                "retrieve": item.get("retrieve"),
                "warnings": item.get("warnings") or [],
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

    tools_map = {
        str(tool["id"]): tool
        for tool in [
            item
            for item in tools_result.data
            if isinstance(item, dict) and item.get("id")
        ]
    }

    return sorted(tools_map.keys()), tools_map, []


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

    completed_map = {
        source["id"]: source
        for source in [
            source
            for source in sources_result.data
            if isinstance(source, dict) and source.get("status") == "completed"
        ]
        if source.get("id")
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


def resolve_effective_session_id(sessions_map: dict[int, dict[str, Any]]) -> int | None:
    """Resolve active session from selector/state and validate against map.

    Args:
        sessions_map: Sessions keyed by ID.

    Returns:
        Valid session ID from state/selector, otherwise None.

    """
    selected_session_id = st.session_state.get("selected_session_id")
    if isinstance(selected_session_id, int) and selected_session_id in sessions_map:
        return selected_session_id

    selector_session_id = st.session_state.get("chat_session_selector")
    if isinstance(selector_session_id, int) and selector_session_id in sessions_map:
        return selector_session_id

    return None


def select_session(client: ApiClient, sessions_map: dict[int, dict[str, Any]]) -> None:
    """Render session selector and synchronize session state.

    Args:
        client: UI API client.
        sessions_map: Sessions keyed by ID.

    """
    session_options: list[int | None] = [None] + sorted(
        sessions_map.keys(), reverse=True
    )

    current_session_id = resolve_effective_session_id(sessions_map=sessions_map)
    st.session_state["selected_session_id"] = current_session_id
    if (
        "chat_session_selector" not in st.session_state
        or st.session_state["chat_session_selector"] not in session_options
        or st.session_state["chat_session_selector"] != current_session_id
    ):
        st.session_state["chat_session_selector"] = current_session_id

    selected_session_id = st.selectbox(
        "Session",
        options=session_options,
        format_func=lambda item: session_label(item, sessions_map),
        key="chat_session_selector",
    )
    if selected_session_id == current_session_id:
        return

    st.session_state["selected_session_id"] = selected_session_id
    if selected_session_id is None:
        st.session_state["selected_session_source_ids"] = []
        return

    st.session_state["selected_session_source_ids"] = list(
        sessions_map[selected_session_id].get("source_ids", [])
    )

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


def render_history(  # noqa: C901
    client: ApiClient, session_id: int | None
) -> list[dict[str, Any]]:
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
            content = str(message.get("content", ""))
            if content:
                st.markdown(content)

            thinking = str(message.get("thinking") or "")
            if role == "assistant" and thinking:
                with st.expander("Thinking", expanded=False):
                    st.markdown(thinking)

            web_search = str(message.get("web_search") or "")
            if role == "assistant" and web_search:
                with st.expander("Web Search", expanded=False):
                    st.markdown(web_search)

            retrieve = str(message.get("retrieve") or "")
            if role == "assistant" and retrieve:
                with st.expander("Retrieve", expanded=False):
                    st.markdown(retrieve)

            warnings = message.get("warnings") or []
            if role == "assistant" and warnings:
                with st.expander("Warnings", expanded=True):
                    for warning in warnings:
                        st.warning(str(warning))

            metadata_text = format_message_metadata(message)
            if metadata_text:
                st.caption(metadata_text)

    return history


def ensure_session_for_prompt(
    client: ApiClient, sessions_map: dict[int, dict[str, Any]]
) -> int | None:
    """Ensure an active session exists before sending a prompt.

    Args:
        client: UI API client.

    Returns:
        Existing or newly created session ID, or None on failure.

    """
    session_id = resolve_effective_session_id(sessions_map=sessions_map)
    if session_id is not None:
        st.session_state["selected_session_id"] = session_id
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
    """Build chat tools payload for the API request.

    Args:
        selected_tool_ids: Tool IDs selected in UI.
        selected_source_ids: Source IDs attached to active session.

    Returns:
        Tools payload for chat request, or None when validation fails.

    """
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
    """Render tool selector and apply source-aware defaults.

    Args:
        tool_ids: Available tool IDs.
        tools_map: Tool metadata keyed by tool ID.

    Returns:
        Tool IDs selected by the user in current rerun.

    """
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
    """Ensure retrieve is selected when sources are selected.

    Args:
        tools_map: Tool metadata keyed by tool ID.

    """
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


def render_tool_result(
    placeholder: Any, title: str, content: str, expanded: bool = True
) -> None:
    """Render tool output inside an expander.

    Args:
        placeholder: Streamlit placeholder used for incremental updates.
        title: Expander title.
        content: Tool output to render.
        expanded: Whether expander is initially expanded.

    """
    with placeholder.container(), st.expander(title, expanded=expanded):
        st.markdown(content)


def send_prompt(  # noqa: C901, PLR0912, PLR0915
    client: ApiClient,
    prompt: str,
    session_id: int,
    provider_id: int,
    model_name: str,
    tool_ids: list[str],
    tools_payload: list[dict[str, Any]],
    live_response_container: Any,
) -> bool:
    """Send a prompt and stream assistant response.

    Args:
        client: UI API client.
        prompt: User prompt text.
        session_id: Active session ID.
        provider_id: Selected provider ID.
        model_name: Selected model name.
        tool_ids: Selected tool IDs.
        tools_payload: Tools payload for backend request.
        live_response_container: Container rendered above chat input.

    Returns:
        True when prompt handling completes, otherwise False on API error.

    """
    history = get_chat_history(session_id=session_id)
    history.append(
        {
            "role": "user",
            "content": prompt,
            "provider_id": provider_id,
            "model_name": model_name,
            "tool_ids": list(tool_ids),
        }
    )
    with live_response_container:
        with st.chat_message("user"):
            st.markdown(prompt)
            metadata_text = format_message_metadata(message=history[-1])
            if metadata_text:
                st.caption(metadata_text)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            thinking_placeholder = st.empty()
            web_search_placeholder = st.empty()
            retrieve_placeholder = st.empty()
            warnings_placeholder = st.empty()
            metadata_placeholder = st.empty()
            final_answer = ""
            final_thinking = ""
            final_web_search = ""
            final_retrieve = ""
            final_warnings: list[str] = []
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
                    thinking = str(chunk.get("thinking") or "")
                    web_search = str(chunk.get("web_search") or "")
                    retrieve = str(chunk.get("retrieve") or "")
                    warnings = chunk.get("warnings") or []
                    model_name_from_chunk = (
                        str(chunk.get("model_name", "")) or model_name
                    )
                    tool_ids_from_chunk = chunk.get("tool_ids") or tool_ids
                    if role == "agent":
                        if content:
                            final_answer = merge_stream_chunk(final_answer, content)
                            placeholder.markdown(final_answer)
                        if thinking:
                            final_thinking = merge_stream_chunk(
                                final_thinking, thinking
                            )
                            render_tool_result(
                                placeholder=thinking_placeholder,
                                title="Thinking",
                                content=final_thinking,
                            )
                        if web_search:
                            final_web_search = merge_stream_chunk(
                                final_web_search, web_search
                            )
                            render_tool_result(
                                placeholder=web_search_placeholder,
                                title="Web Search",
                                content=final_web_search,
                            )
                        if retrieve:
                            final_retrieve = merge_stream_chunk(
                                final_retrieve, retrieve
                            )
                            render_tool_result(
                                placeholder=retrieve_placeholder,
                                title="Retrieve",
                                content=final_retrieve,
                            )
                        if warnings:
                            for warning in warnings:
                                warning_text = str(warning)
                                if warning_text in final_warnings:
                                    continue
                                final_warnings.append(warning_text)
                            with (
                                warnings_placeholder.container(),
                                st.expander("Warnings", expanded=True),
                            ):
                                for warning in final_warnings:
                                    st.warning(warning)
                        chunk_model_name = model_name_from_chunk
                        chunk_tool_ids = [
                            str(tool_id) for tool_id in tool_ids_from_chunk
                        ]
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
                return False

    if (
        final_answer
        or final_thinking
        or final_web_search
        or final_retrieve
        or final_warnings
    ):
        history.append(
            {
                "role": "agent",
                "content": final_answer,
                "thinking": final_thinking or None,
                "web_search": final_web_search or None,
                "retrieve": final_retrieve or None,
                "provider_id": provider_id,
                "model_name": chunk_model_name,
                "tool_ids": chunk_tool_ids,
                "warnings": final_warnings,
            }
        )

    return True


def handle_prompt_submission(
    client: ApiClient,
    sessions_map: dict[int, dict[str, Any]],
    selected_provider_id: int,
    selected_model_name: str,
    selected_tool_ids: list[str],
    live_response_container: Any,
) -> None:
    """Handle chat input submit and response rendering for a single rerun.

    Args:
        client: UI API client.
        sessions_map: Sessions keyed by ID.
        selected_provider_id: Currently selected provider ID.
        selected_model_name: Currently selected model name.
        selected_tool_ids: Tool IDs selected for current request.
        live_response_container: Streamlit container for live assistant output.

    """
    prompt = st.chat_input("Write a message")
    if not prompt:
        return

    tools_payload = build_chat_tools_payload(
        selected_tool_ids=selected_tool_ids,
        selected_source_ids=st.session_state["selected_session_source_ids"],
    )
    if tools_payload is None:
        return

    active_session_id = ensure_session_for_prompt(
        client=client, sessions_map=sessions_map
    )
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
        live_response_container=live_response_container,
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

    render_history(client=client, session_id=st.session_state["selected_session_id"])

    handle_prompt_submission(
        client=client,
        sessions_map=sessions_map,
        selected_provider_id=selected_provider_id,
        selected_model_name=selected_model_name,
        selected_tool_ids=selected_tool_ids,
        live_response_container=st.container(),
    )
