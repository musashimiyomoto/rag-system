import streamlit as st

from ui.api import ApiClient
from ui.tabs import render_chat_tab, render_providers_tab, render_sources_tab
from ui.utils import init_state


def main() -> None:
    """Configure and render all Streamlit tabs."""
    st.set_page_config(page_title="RAG System UI", layout="wide")
    st.title("RAG System UI")

    init_state()

    client = ApiClient(base_url="http://api:5000")
    for tab, render in zip(
        st.tabs(["Sources", "Chat", "Providers"]),
        [render_sources_tab, render_chat_tab, render_providers_tab],
        strict=True,
    ):
        with tab:
            render(client=client)


if __name__ == "__main__":
    main()
