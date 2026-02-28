import streamlit as st

from ui.api import ApiClient
from ui.utils import show_result, show_table


def render_providers_tab(client: ApiClient) -> None:
    """Render the Providers tab.

    Args:
        client: UI API client.

    """
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
