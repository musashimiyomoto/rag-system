from typing import Annotated

from fastapi import Body, Depends
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from ai.agent import generate_agent
from ai.dependencies import AgentDeps
from api.dependencies import db
from schemas import ChatRequest


async def get_agent(
    data: Annotated[ChatRequest, Body(default=...)],
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
) -> Agent[AgentDeps, str]:
    """Get agent instance by provider runtime configuration.

    Args:
        session: The database session.
        data: The chat request data.

    Returns:
        The agent instance.

    """
    return await generate_agent(
        session=session,
        provider_id=data.provider_id,
        model_name=data.model_name,
        tool_ids=[tool.id for tool in data.tools],
    )
