from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import Dependencies
from ai.model import get_model
from ai.prompts import SYSTEM_PROMPT
from ai.tools import retrieve
from db.repositories import ProviderRepository, SourceRepository
from exceptions import ProviderConflictError, ProviderNotFoundError
from utils import decrypt


async def generate_agent(
    session: AsyncSession, provider_id: int, model_name: str
) -> Agent[Dependencies, str]:
    """Generate the agent.

    Args:
        session: The database session.
        provider_id: The provider ID.
        model_name: The model name.

    Returns:
        The agent.

    """
    provider = await ProviderRepository().get_by(session=session, id=provider_id)

    if not provider:
        raise ProviderNotFoundError
    if not provider.is_active:
        raise ProviderConflictError(message="Provider is inactive")

    model, model_settings = get_model(
        provider_name=provider.name,
        model_name=model_name,
        api_key=decrypt(encrypted_data=provider.api_key_encrypted),
    )

    agent = Agent(
        model=model,
        tools=[retrieve],
        deps_type=Dependencies,
        model_settings=model_settings,
    )

    @agent.instructions
    async def generate_instructions(context: RunContext[Dependencies]) -> str:
        source_summaries = []
        for source_id in context.deps.source_ids:
            source = await SourceRepository().get_by(
                session=context.deps.session, id=source_id
            )
            if not source:
                continue

            source_summaries.append(
                f"[source:{source.id}] {source.name}\n"
                f"{source.summary or 'Empty summary'}"
            )

        return SYSTEM_PROMPT.format(
            source_summary="\n\n".join(source_summaries)
            if source_summaries
            else "Empty summary"
        )

    return agent
