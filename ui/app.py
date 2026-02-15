from typing import Any

import streamlit as st

from ui.api_client import ApiClient, ApiClientError
from ui.components import show_result, show_table
from ui.state import get_chat_history, init_state


def render_health_tab(client: ApiClient) -> None:
    st.subheader("Service Health")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Check liveness", use_container_width=True):
            show_result(client.liveness())
    with col2:
        if st.button("Check readiness", use_container_width=True):
            show_result(client.readiness())


def render_sources_tab(client: ApiClient) -> None:
    st.subheader("Upload Source")
    with st.form("upload_source"):
        file = st.file_uploader("Choose file", type=["pdf", "txt"])
        submitted = st.form_submit_button("Upload")
        if submitted:
            if not file:
                st.warning("Choose a file first")
            else:
                result = client.create_source(file.name, file.getvalue())
                show_result(result, "Source uploaded")

    st.divider()
    if st.button("Refresh sources", key="refresh_sources"):
        pass
    sources_result = client.list_sources()
    if sources_result.ok and isinstance(sources_result.data, list):
        show_table(sources_result.data, "Sources")
    else:
        show_result(sources_result)

    st.divider()
    st.subheader("Get source by ID")
    source_id = st.number_input(
        "Source ID",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_source_id"]),
        key="source_id_get",
    )
    if st.button("Get source", key="get_source"):
        st.session_state["selected_source_id"] = int(source_id)
        show_result(client.get_source(int(source_id)))

    st.subheader("Delete source")
    delete_id = st.number_input(
        "Source ID to delete",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_source_id"]),
        key="source_id_delete",
    )
    if st.button("Delete source", key="delete_source"):
        st.session_state["selected_source_id"] = int(delete_id)
        show_result(client.delete_source(int(delete_id)))


def render_sessions_tab(client: ApiClient) -> None:
    st.subheader("Create Session")
    sources = client.list_sources()
    source_options: dict[str, int] = {}
    if sources.ok and isinstance(sources.data, list):
        for item in sources.data:
            source_id = item.get("id")
            if source_id is None:
                continue
            source_name = item.get("name", "unknown")
            source_status = item.get("status", "unknown")
            label = f"{source_id} - {source_name} ({source_status})"
            source_options[label] = int(source_id)

    with st.form("create_session"):
        selected = st.multiselect(
            "Source IDs",
            options=list(source_options.keys()),
            help="Prefer sources with COMPLETED status",
        )
        submitted = st.form_submit_button("Create session")
        if submitted:
            ids = [source_options[label] for label in selected]
            result = client.create_session(ids)
            if result.ok and isinstance(result.data, dict) and result.data.get("id"):
                st.session_state["selected_session_id"] = int(result.data["id"])
            show_result(result, "Session created")

    st.divider()
    st.subheader("Session Messages")
    session_id = st.number_input(
        "Session ID",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_session_id"]),
        key="messages_session_id",
    )
    if st.button("Load messages", key="load_messages"):
        st.session_state["selected_session_id"] = int(session_id)
        messages = client.list_messages(int(session_id))
        if messages.ok and isinstance(messages.data, list):
            history = [
                {
                    "role": str(item.get("role", "")),
                    "content": str(item.get("content", "")),
                }
                for item in messages.data
            ]
            st.session_state["chat_history"][str(int(session_id))] = history
        show_result(messages)

    st.subheader("Delete Session")
    session_delete_id = st.number_input(
        "Session ID to delete", min_value=1, step=1, key="delete_session_id"
    )
    if st.button("Delete session", key="delete_session"):
        show_result(client.delete_session(int(session_delete_id)))


def render_chat_model_selector(client: ApiClient) -> str:
    provider_id = st.number_input(
        "Provider ID",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_provider_id"]),
        key="chat_provider_id",
    )
    st.session_state["selected_provider_id"] = int(provider_id)

    models_result = client.provider_models(int(provider_id))
    if models_result.ok and isinstance(models_result.data, list):
        model_names = [
            str(item.get("name", ""))
            for item in models_result.data
            if isinstance(item, dict) and item.get("name")
        ]
    else:
        model_names = []
        show_result(models_result)

    if model_names:
        try:
            current_index = model_names.index(st.session_state["selected_model_name"])
        except ValueError:
            current_index = 0
        selected_model_name = st.selectbox(
            "Model",
            options=model_names,
            index=current_index,
            key="chat_model_name",
        )
    else:
        selected_model_name = st.text_input(
            "Model name",
            value=str(st.session_state["selected_model_name"]),
            key="chat_model_name_fallback",
        )

    st.session_state["selected_model_name"] = selected_model_name
    return selected_model_name


def merge_stream_chunk(current_text: str, chunk_text: str) -> str:
    """Merge streamed chunk for both cumulative and delta streaming styles."""
    if not chunk_text:
        return current_text
    if chunk_text == current_text:
        return current_text
    if chunk_text.startswith(current_text):
        return chunk_text
    if current_text.endswith(chunk_text):
        return current_text
    return current_text + chunk_text


def render_chat_tab(client: ApiClient) -> None:
    st.subheader("Chat")
    selected_model_name = render_chat_model_selector(client)

    current_session_id = st.number_input(
        "Session ID",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_session_id"]),
        key="chat_session_id",
    )
    st.session_state["selected_session_id"] = int(current_session_id)

    history = get_chat_history(int(current_session_id))
    for message in history:
        role = "assistant" if message.get("role") == "agent" else "user"
        with st.chat_message(role):
            st.markdown(message.get("content", ""))

    prompt = st.chat_input("Write a message")
    if not prompt:
        return
    if not selected_model_name:
        st.warning("Select model_name before sending message")
        return

    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        final_answer = ""
        try:
            for chunk in client.stream_chat(
                int(current_session_id),
                prompt,
                int(st.session_state["selected_provider_id"]),
                selected_model_name,
            ):
                role = str(chunk.get("role", ""))
                content = str(chunk.get("content", ""))
                if role == "agent":
                    final_answer = merge_stream_chunk(final_answer, content)
                    placeholder.markdown(final_answer)
        except ApiClientError as exc:
            st.error(f"HTTP {exc.status_code}: {exc.detail}")
            return

    if final_answer:
        history.append({"role": "agent", "content": final_answer})


def render_providers_tab(client: ApiClient) -> None:
    st.subheader("Create Provider")
    with st.form("create_provider"):
        provider_name = st.selectbox("Provider", options=["openai", "google"])
        api_key = st.text_input("API Key", type="password")
        submitted = st.form_submit_button("Create provider")
        if submitted:
            result = client.create_provider(provider_name, api_key)
            show_result(result, "Provider created")

    st.divider()
    if st.button("Refresh providers", key="refresh_providers"):
        pass
    providers = client.list_providers()
    if providers.ok and isinstance(providers.data, list):
        show_table(providers.data, "Providers")
    else:
        show_result(providers)

    st.subheader("Update Provider")
    with st.form("update_provider"):
        provider_id = st.number_input(
            "Provider ID",
            min_value=1,
            step=1,
            value=int(st.session_state["selected_provider_id"]),
        )
        new_api_key = st.text_input("New API Key (optional)", type="password")
        is_active_raw = st.selectbox(
            "is_active", options=["unchanged", "true", "false"]
        )
        is_active: bool | None
        if is_active_raw == "true":
            is_active = True
        elif is_active_raw == "false":
            is_active = False
        else:
            is_active = None
        submitted = st.form_submit_button("Update provider")
        if submitted:
            st.session_state["selected_provider_id"] = int(provider_id)
            result = client.update_provider(
                int(provider_id), new_api_key or None, is_active
            )
            show_result(result, "Provider updated")

    st.subheader("Provider Models")
    model_provider_id = st.number_input(
        "Provider ID for models",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_provider_id"]),
        key="provider_models_id",
    )
    if st.button("Get models", key="get_provider_models"):
        st.session_state["selected_provider_id"] = int(model_provider_id)
        show_result(client.provider_models(int(model_provider_id)))

    st.subheader("Delete Provider")
    delete_provider_id = st.number_input(
        "Provider ID to delete",
        min_value=1,
        step=1,
        value=int(st.session_state["selected_provider_id"]),
        key="provider_delete_id",
    )
    if st.button("Delete provider", key="delete_provider"):
        st.session_state["selected_provider_id"] = int(delete_provider_id)
        show_result(client.delete_provider(int(delete_provider_id)))


def main() -> None:
    st.set_page_config(page_title="RAG System UI", layout="wide")
    st.title("RAG System UI")

    init_state()
    api_base_url = st.sidebar.text_input(
        "API Base URL", value=st.session_state["api_base_url"]
    )
    st.session_state["api_base_url"] = api_base_url
    client = ApiClient(base_url=api_base_url)

    tabs = st.tabs(["Health", "Sources", "Sessions", "Chat", "Providers"])
    renderers: list[tuple[Any, Any]] = [
        (tabs[0], render_health_tab),
        (tabs[1], render_sources_tab),
        (tabs[2], render_sessions_tab),
        (tabs[3], render_chat_tab),
        (tabs[4], render_providers_tab),
    ]
    for tab, renderer in renderers:
        with tab:
            renderer(client)


if __name__ == "__main__":
    main()
