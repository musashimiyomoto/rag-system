from typing import Annotated

from fastapi import Query
from pydantic_ai import Agent

from ai.agent import generate_agent
from ai.dependencies import Dependencies
from enums import LLMName


def get_agent(
    llm: Annotated[LLMName, Query()] = LLMName.OPENAI_GPT_5_NANO,
) -> Agent[Dependencies, str]:
    """Get the agent instance.

    Args:
        llm: The llm name.

    Returns:
        The agent instance.

    """
    return generate_agent(llm=llm)
