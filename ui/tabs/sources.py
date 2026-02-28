import streamlit as st

from ui.api import ApiClient
from ui.models import ApiResult
from ui.utils import show_result, show_table, source_label

UPLOAD_DISABLED_MESSAGE = (
    "Upload disabled: configure and activate at least one provider for source "
    "summarization. Go to Providers tab, create provider, set active."
)
SOURCE_TYPES_UNAVAILABLE_MESSAGE = (
    "Upload disabled: could not load supported source types from backend."
)


def get_provider_upload_state(providers_result: ApiResult) -> tuple[int, bool]:
    """Compute source upload availability from providers response.

    Args:
        providers_result: Provider list API response.

    Returns:
        Active provider count and upload-enabled flag.

    """
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
    """Detach a source from the selected session before deletion.

    Args:
        client: UI API client.
        session_id: Active session ID.
        source_id: Source ID to remove from the session.

    Returns:
        True when detaching is not required or completed successfully.

    """
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


def get_supported_source_types(client: ApiClient) -> list[str]:
    """Get supported source types from backend.

    Args:
        client: UI API client.

    Returns:
        Supported source types list or an empty list on failure.

    """
    source_types_result = client.list_source_types()
    if source_types_result.ok and isinstance(source_types_result.data, list):
        return [str(source_type) for source_type in source_types_result.data]

    if not source_types_result.ok:
        show_result(source_types_result)

    return []


def render_upload_form(
    client: ApiClient, source_types: list[str], upload_enabled: bool
) -> None:
    """Render source upload form.

    Args:
        client: UI API client.
        source_types: Supported source types.
        upload_enabled: Upload enabled flag.

    """
    with st.form("upload_source"):
        file = st.file_uploader("Upload source", type=source_types)
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


def _render_db_credentials_inputs(
    source_type: str,
) -> tuple[dict[str, object], str | None]:
    """Render DB credentials form fields and return values."""
    host = st.text_input("Host", key="db_source_host", value="")
    default_port = 5432 if source_type == "postgres" else 8123
    port = st.number_input(
        "Port",
        key="db_source_port",
        min_value=1,
        max_value=65535,
        value=default_port,
        step=1,
    )
    database = st.text_input("Database", key="db_source_database", value="")
    user = st.text_input("User", key="db_source_user", value="")
    password = st.text_input(
        "Password", key="db_source_password", value="", type="password"
    )

    schema_hint = (
        "Schema (optional, default public)"
        if source_type == "postgres"
        else "Database override (optional)"
    )
    schema_filter = st.text_input(schema_hint, key="db_source_schema_filter", value="")

    credentials: dict[str, object] = {
        "host": host,
        "port": int(port),
        "database": database,
        "user": user,
        "password": password,
    }
    if source_type == "postgres":
        sslmode = st.text_input(
            "SSL mode (optional)", key="db_source_sslmode", value=""
        )
        if sslmode:
            credentials["sslmode"] = sslmode
    else:
        secure = st.checkbox("HTTPS/secure", key="db_source_secure", value=False)
        credentials["secure"] = secure

    return credentials, (schema_filter or None)


def _load_db_tables(client: ApiClient, upload_enabled: bool) -> None:
    """Load DB table metadata and store in session state."""
    st.markdown("### Database source")

    source_type = st.selectbox(
        "DB type",
        options=["postgres", "clickhouse"],
        key="db_source_type",
    )
    credentials, schema_filter = _render_db_credentials_inputs(source_type=source_type)

    if st.button(
        "Load tables", key="db_source_load_tables", disabled=not upload_enabled
    ):
        introspect_result = client.introspect_db_source(
            source_type=source_type,
            credentials=credentials,
            schema=schema_filter,
        )
        if not introspect_result.ok:
            st.session_state["db_source_tables"] = []
            show_result(introspect_result)
            return

        tables = (
            introspect_result.data.get("tables", [])
            if isinstance(introspect_result.data, dict)
            else []
        )
        st.session_state["db_source_tables"] = tables
        st.session_state["db_source_last_credentials"] = credentials
        st.session_state["db_source_last_type"] = source_type
        show_result(introspect_result, "Tables loaded")


def _render_db_mapping_and_create(client: ApiClient, upload_enabled: bool) -> None:
    """Render DB mapping selectors and create action."""
    tables = st.session_state.get("db_source_tables", [])
    if not isinstance(tables, list) or len(tables) == 0:
        st.info("Load tables to configure DB source")
        return

    table_options = [
        (str(item.get("schema", "")), str(item.get("table", "")))
        for item in tables
        if isinstance(item, dict)
    ]
    if len(table_options) == 0:
        st.info("No tables returned by introspection")
        return

    selected_table = st.selectbox(
        "Table",
        options=table_options,
        format_func=lambda item: f"{item[0]}.{item[1]}",
        key="db_source_table",
    )

    selected_schema, selected_table_name = selected_table
    selected_columns = []
    for table in tables:
        if (
            isinstance(table, dict)
            and table.get("schema") == selected_schema
            and table.get("table") == selected_table_name
        ):
            selected_columns = [
                str(column.get("name"))
                for column in table.get("columns", [])
                if isinstance(column, dict) and column.get("name")
            ]
            break

    if len(selected_columns) == 0:
        st.warning("Selected table has no columns")
        return

    id_field = st.selectbox(
        "id_field", options=selected_columns, key="db_source_id_field"
    )
    search_field = st.selectbox(
        "search_field", options=selected_columns, key="db_source_search_field"
    )
    filter_fields = st.multiselect(
        "filter_fields",
        options=selected_columns,
        default=[],
        key="db_source_filter_fields",
    )
    source_name = st.text_input(
        "Source name (optional)",
        key="db_source_name",
        value="",
    )

    if st.button(
        "Create DB source", key="db_source_create", disabled=not upload_enabled
    ):
        source_type = st.session_state.get(
            "db_source_last_type"
        ) or st.session_state.get("db_source_type")
        credentials = st.session_state.get("db_source_last_credentials")
        if not isinstance(credentials, dict):
            st.warning("Load tables first")
            return

        create_result = client.create_db_source(
            source_type=str(source_type),
            credentials=credentials,
            schema_name=selected_schema,
            table_name=selected_table_name,
            id_field=id_field,
            search_field=search_field,
            filter_fields=filter_fields,
            name=(source_name or None),
        )
        show_result(create_result, "DB source created")


def render_db_source_form(client: ApiClient, upload_enabled: bool) -> None:
    """Render DB source introspection and creation form."""
    with st.container(border=True):
        _load_db_tables(client=client, upload_enabled=upload_enabled)
        _render_db_mapping_and_create(client=client, upload_enabled=upload_enabled)


def render_sources_tab(client: ApiClient) -> None:
    """Render the Sources tab.

    Args:
        client: UI API client.

    """
    st.subheader("Sources")

    providers_result = client.list_providers()
    if not providers_result.ok:
        show_result(providers_result)
    active_provider_count, upload_enabled = get_provider_upload_state(providers_result)

    st.caption(f"Active providers: {active_provider_count}")
    if not upload_enabled:
        st.warning(UPLOAD_DISABLED_MESSAGE)

    source_types = get_supported_source_types(client=client)
    if len(source_types) == 0:
        st.warning(SOURCE_TYPES_UNAVAILABLE_MESSAGE)
        upload_enabled = False

    render_upload_form(
        client=client, source_types=source_types, upload_enabled=upload_enabled
    )
    render_db_source_form(client=client, upload_enabled=upload_enabled)

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
