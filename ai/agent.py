from pydantic_ai import Agent, RunContext

from ai.dependencies import Dependencies
from ai.model import get_model
from ai.prompts import SYSTEM_PROMPT
from ai.tools import retrieve
from db.repositories import SourceRepository
from enums import LLMName


def generate_agent(llm: LLMName) -> Agent[Dependencies, str]:
    """Generate the agent.

    Args:
        llm: The large language model name.

    Returns:
        The agent.

    """
    model, model_settings = get_model(llm=llm)

    agent = Agent(
        model=model,
        tools=[retrieve],
        deps_type=Dependencies,
        model_settings=model_settings,
    )

    @agent.instructions
    async def generate_instructions(context: RunContext[Dependencies]) -> str:
        source = await SourceRepository().get_by(
            session=context.deps.session, id=context.deps.source_id
        )
        if not source:
            return SYSTEM_PROMPT.format(source_summary="Empty summary")

        return SYSTEM_PROMPT.format(source_summary=source.summary)

    return agent
