from typing import Any

import streamlit as st

from ui.api import ApiClient
from ui.components import show_result, show_table
from ui.exceptions import ApiClientError
from ui.state import get_chat_history, init_state


def source_label(source: dict[str, Any]) -> str:
    source_id = source["id"]
    source_name = source.get("name", "unknown")
    source_status = source.get("status", "unknown")
    return f"{source_id} - {source_name} ({source_status})"


def provider_label(provider: dict[str, Any]) -> str:
    provider_id = provider["id"]
    provider_name = provider.get("name", "unknown")
    status = "active" if provider.get("is_active") else "inactive"
    return f"{provider_id} - {provider_name} [{status}]"


def tool_label(tool: dict[str, Any]) -> str:
    tool_id = str(tool.get("id", "unknown"))
    tool_title = str(tool.get("title", tool_id))
    return f"{tool_title} ({tool_id})"


def session_label(
    session_item: int | None, sessions_map: dict[int, dict[str, Any]]
) -> str:
    if session_item is None:
        return "No active session"
    source_ids = sessions_map.get(session_item, {}).get("source_ids", [])
    return f"Session #{session_item} ({len(source_ids)} sources)"


def merge_stream_chunk(current_text: str, chunk_text: str) -> str:
    if not chunk_text:
        return current_text
    if chunk_text == current_text:
        return current_text
    if chunk_text.startswith(current_text):
        return chunk_text
    if current_text.endswith(chunk_text):
        return current_text
    return current_text + chunk_text


def load_session_messages(client: ApiClient, session_id: int) -> None:
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


def render_sources_tab(client: ApiClient) -> None:
    st.subheader("Sources")
    with st.form("upload_source"):
        file = st.file_uploader(
            "Upload source",
            type=[
                "pdf",
                "txt",
                "md",
                "docx",
                "rtf",
                "odt",
                "epub",
                "html",
                "htm",
                "pptx",
                "xlsx",
                "eml",
            ],
        )
        submitted = st.form_submit_button("Upload")
        if submitted:
            if not file:
                st.warning("Choose file")
            else:
                upload_result = client.create_source(
                    filename=file.name,
                    file_content=file.getvalue(),
                )
                show_result(upload_result, "Source uploaded")

    sources_result = client.list_sources()
    if not (sources_result.ok and isinstance(sources_result.data, list)):
        show_result(sources_result)
        return

    sources = sources_result.data
    show_table(sources, "Sources list")

    source_map = {source["id"]: source for source in sources if source.get("id")}
    source_ids = sorted(source_map.keys())
    if not source_ids:
        st.info("No sources to delete")
        return

    selected_source_id = st.selectbox(
        "Source to delete",
        options=source_ids,
        format_func=lambda source_id: source_label(source_map[source_id]),
        key="delete_source_selector",
    )

    if st.button("Delete selected source", key="delete_selected_source"):
        current_session_id = st.session_state["selected_session_id"]
        if current_session_id is not None:
            detach_result = detach_source_from_current_session(
                client=client,
                session_id=int(current_session_id),
                source_id=selected_source_id,
            )
            if detach_result is False:
                return

        delete_result = client.delete_source(source_id=selected_source_id)
        show_result(delete_result, "Source deleted")


def detach_source_from_current_session(
    client: ApiClient, session_id: int, source_id: int
) -> bool:
    sessions_result = client.list_sessions()
    if not (sessions_result.ok and isinstance(sessions_result.data, list)):
        show_result(sessions_result)
        return False

    sessions_map = {
        item["id"]: item
        for item in sessions_result.data
        if isinstance(item, dict) and item.get("id")
    }
    current_session = sessions_map.get(session_id)
    if not current_session:
        return True

    current_source_ids = current_session.get("source_ids", [])
    if source_id not in current_source_ids:
        return True

    updated_source_ids = [item for item in current_source_ids if item != source_id]
    update_result = client.update_session(
        session_id=session_id,
        source_ids=updated_source_ids,
    )
    if not update_result.ok:
        show_result(update_result)
        return False

    st.session_state["selected_session_source_ids"] = updated_source_ids
    return True


def get_provider_context(
    client: ApiClient,
) -> tuple[int, str] | None:
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
    tools_result = client.list_tools()
    if not (tools_result.ok and isinstance(tools_result.data, list)):
        show_result(tools_result)
        return None

    tools = [
        item for item in tools_result.data if isinstance(item, dict) and item.get("id")
    ]
    tools_map = {str(tool["id"]): tool for tool in tools}
    tool_ids = sorted(tools_map.keys())
    default_tool_ids = [
        str(tool["id"]) for tool in tools if bool(tool.get("enabled_by_default"))
    ]
    return tool_ids, tools_map, default_tool_ids


def get_completed_sources(
    client: ApiClient,
) -> tuple[list[int], dict[int, dict[str, Any]]] | None:
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


def _format_message_metadata(message: dict[str, Any]) -> str:
    model_name = str(message.get("model_name") or "")
    tool_ids = message.get("tool_ids") or []
    if not model_name and not tool_ids:
        return ""
    tools_text = ", ".join(str(tool_id) for tool_id in tool_ids) if tool_ids else "-"
    model_text = model_name or "-"
    return f"`model: {model_text} | tools: {tools_text}`"


def render_history(client: ApiClient, session_id: int | None) -> list[dict[str, Any]]:
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
            metadata_text = _format_message_metadata(message)
            if metadata_text:
                st.caption(metadata_text)

    return history


def ensure_session_for_prompt(client: ApiClient) -> int | None:
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


def send_prompt(
    client: ApiClient,
    prompt: str,
    session_id: int,
    provider_id: int,
    model_name: str,
    tool_ids: list[str],
) -> None:
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
        metadata_text = _format_message_metadata(history[-1])
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
                tool_ids=tool_ids,
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
                        _format_message_metadata(
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
    st.subheader("Chat")

    provider_context = get_provider_context(client=client)
    if provider_context is None:
        return
    selected_provider_id, selected_model_name = provider_context

    tools_context = get_tool_context(client=client)
    if tools_context is None:
        return
    tool_ids, tools_map, default_tool_ids = tools_context
    if not st.session_state["selected_tool_ids"]:
        st.session_state["selected_tool_ids"] = default_tool_ids
    selected_tool_ids = st.multiselect(
        "Tools for this request",
        options=tool_ids,
        default=[
            tool_id
            for tool_id in st.session_state["selected_tool_ids"]
            if tool_id in tools_map
        ],
        format_func=lambda tool_id: tool_label(tools_map[tool_id]),
        key="chat_tools_selector",
    )
    st.session_state["selected_tool_ids"] = selected_tool_ids

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

    current_session_id = st.session_state["selected_session_id"]
    render_history(client=client, session_id=current_session_id)

    prompt = st.chat_input("Write a message")
    if not prompt:
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
    )


def render_providers_tab(client: ApiClient) -> None:
    st.subheader("Providers")
    with st.form("create_provider"):
        provider_name = st.selectbox("Provider", options=["openai", "google"])
        api_key = st.text_input("API Key", type="password")
        submitted = st.form_submit_button("Create provider")
        if submitted:
            create_result = client.create_provider(name=provider_name, api_key=api_key)
            show_result(create_result, "Provider created")

    providers = client.list_providers()
    if providers.ok and isinstance(providers.data, list):
        show_table(providers.data, "Providers list")
    else:
        show_result(providers)


def main() -> None:
    st.set_page_config(page_title="RAG System UI", layout="wide")
    st.title("RAG System UI")
    init_state()

    client = ApiClient(base_url="http://api:5000")
    tabs = st.tabs(["Sources", "Chat", "Providers"])
    with tabs[0]:
        render_sources_tab(client)
    with tabs[1]:
        render_chat_tab(client)
    with tabs[2]:
        render_providers_tab(client)


if __name__ == "__main__":
    main()
