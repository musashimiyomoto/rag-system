from typing import Annotated

from fastapi import Depends, Query
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from ai.agent import generate_agent
from ai.dependencies import Dependencies
from api.dependencies import db


async def get_agent(
    session: Annotated[AsyncSession, Depends(dependency=db.get_session)],
    provider_id: Annotated[int, Query(default=..., gt=0)],
    model_name: Annotated[str, Query(default=..., min_length=1)],
) -> Agent[Dependencies, str]:
    """Get agent instance by provider runtime configuration.

    Args:
        session: The database session.
        provider_id: The provider ID.
        model_name: The model name.

    Returns:
        The agent instance.

    """
    return await generate_agent(
        session=session, provider_id=provider_id, model_name=model_name
    )
