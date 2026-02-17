import pytest

from ai.deps_builder import build_agent_deps
from enums import ToolId
from tests.factories import SessionFactory, SessionSourceFactory, SourceFactory


@pytest.mark.asyncio
async def test_build_agent_deps_with_retrieve(test_session) -> None:
    source = await SourceFactory.create_async(session=test_session)
    chat_session = await SessionFactory.create_async(session=test_session)
    await SessionSourceFactory.create_async(
        session=test_session, session_id=chat_session.id, source_id=source.id
    )

    deps = await build_agent_deps(
        session=test_session, session_id=chat_session.id, tool_ids=[ToolId.RETRIEVE]
    )

    assert deps.session_id == chat_session.id
    assert deps.source_ids == [source.id]
    assert deps.tool_context.retrieve is not None
    assert deps.tool_context.retrieve.allowed_source_ids == [source.id]
    assert deps.tool_context.web_search is None


@pytest.mark.asyncio
async def test_build_agent_deps_with_web_search_only(test_session) -> None:
    chat_session = await SessionFactory.create_async(session=test_session)

    deps = await build_agent_deps(
        session=test_session, session_id=chat_session.id, tool_ids=[ToolId.WEB_SEARCH]
    )

    assert deps.tool_context.retrieve is None
    assert deps.tool_context.web_search is not None


@pytest.mark.asyncio
async def test_build_agent_deps_uses_default_tools(test_session) -> None:
    chat_session = await SessionFactory.create_async(session=test_session)

    deps = await build_agent_deps(
        session=test_session, session_id=chat_session.id, tool_ids=[]
    )

    assert deps.tool_context.retrieve is not None
    assert deps.tool_context.web_search is not None
