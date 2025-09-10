from pydantic_ai import Agent, RunContext

from ai.dependencies import Dependencies
from ai.model import get_model
from ai.prompts import SYSTEM_PROMPT
from ai.tools import retrieve
from db.repositories import DocumentRepository
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

    @agent.system_prompt
    async def generate_system_prompt(context: RunContext[Dependencies]) -> str:
        document = await DocumentRepository().get_by(
            session=context.deps.session, id=context.deps.document_id
        )
        if not document:
            return SYSTEM_PROMPT

        return SYSTEM_PROMPT + f"\n\nDocument Summary: {document.summary}"

    return agent
