from typing import Any

import streamlit as st

from ui.api_client import ApiResult


def show_result(result: ApiResult, success_message: str | None = None) -> None:
    if result.ok:
        if success_message:
            st.success(success_message)
        if result.data is not None:
            st.json(result.data)
        return

    detail = format_error_detail(result.detail)
    st.error(f"HTTP {result.status_code}: {detail}")


def show_table(data: list[dict[str, Any]], title: str | None = None) -> None:
    if title:
        st.subheader(title)
    if not data:
        st.info("No data")
        return
    st.dataframe(data, use_container_width=True)


def format_error_detail(detail: str | None) -> str:
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
