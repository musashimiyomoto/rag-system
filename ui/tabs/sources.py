import streamlit as st

from ui.api import ApiClient
from ui.models import ApiResult
from ui.utils import show_result, show_table, source_label

SUPPORTED_SOURCE_TYPES = [
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
]

UPLOAD_DISABLED_MESSAGE = (
    "Upload disabled: configure and activate at least one provider for source "
    "summarization. Go to Providers tab, create provider, set active."
)


def get_provider_upload_state(providers_result: ApiResult) -> tuple[int, bool]:
    """Return active provider count and whether source upload is allowed."""
    if not (providers_result.ok and isinstance(providers_result.data, list)):
        return 0, False

    active_provider_count = sum(
        1
        for provider in providers_result.data
        if isinstance(provider, dict) and provider.get("is_active")
    )
    return active_provider_count, active_provider_count > 0


def detach_source_from_current_session(
    client: ApiClient, session_id: int, source_id: int
) -> bool:
    """Detach source from the selected session before source deletion."""
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


def render_sources_tab(client: ApiClient) -> None:
    """Render source upload/list/delete tab."""
    st.subheader("Sources")

    providers_result = client.list_providers()
    if not providers_result.ok:
        show_result(providers_result)
    active_provider_count, upload_enabled = get_provider_upload_state(providers_result)

    st.caption(f"Active providers: {active_provider_count}")
    if not upload_enabled:
        st.warning(UPLOAD_DISABLED_MESSAGE)

    with st.form("upload_source"):
        file = st.file_uploader("Upload source", type=SUPPORTED_SOURCE_TYPES)
        submitted = st.form_submit_button("Upload", disabled=not upload_enabled)
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
