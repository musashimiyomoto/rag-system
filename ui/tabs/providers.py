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
        submitted = st.form_submit_button("Create provider")
        if submitted:
            show_result(
                result=client.create_provider(
                    name=st.selectbox(
                        "Provider",
                        options=["openai", "google", "anthropic", "github", "ollama"],
                    ),
                    api_key=st.text_input(
                        "API Key (optional only for ollama)", type="password"
                    ).strip()
                    or None,
                ),
                success_message="Provider created",
            )

    providers = client.list_providers()
    if providers.ok and isinstance(providers.data, list):
        show_table(data=providers.data, title="Providers list")
    else:
        show_result(result=providers)
