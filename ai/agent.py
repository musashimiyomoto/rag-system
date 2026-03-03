from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps
from ai.model import get_model
from ai.prompts import SYSTEM_PROMPT
from ai.tools import TOOL_REGISTRY, get_tools
from db.repositories import ProviderRepository, SourceRepository
from enums import ToolId
from exceptions import ProviderConflictError, ProviderNotFoundError
from utils import decrypt


def _render_selected_tools_context(tool_ids: list[ToolId]) -> str:
    """Render selected tools for the system prompt."""
    if not tool_ids:
        return "No tools selected for this run."

    lines = []
    for tool_id in tool_ids:
        spec = TOOL_REGISTRY.get(tool_id)
        if not spec:
            continue

        lines.append(f"- {spec.id}: {spec.description}")

    if not lines:
        return "No tools selected for this run."

    return "\n".join(lines)


async def generate_agent(
    session: AsyncSession, provider_id: int, model_name: str, tool_ids: list[ToolId]
) -> Agent[AgentDeps, str]:
    """Generate the agent.

    Args:
        session: The database session.
        provider_id: The provider ID.
        model_name: The model name.
        tool_ids: List of tool ids.

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
        tools=get_tools(tool_ids=tool_ids),
        deps_type=AgentDeps,
        model_settings=model_settings,
    )

    @agent.instructions
    async def generate_instructions(context: RunContext[AgentDeps]) -> str:
        """Generate instructions.

        Args:
            context: The context parameter.

        Returns:
            The rendered system prompt with source summaries.

        """
        selected_tools_context = _render_selected_tools_context(tool_ids=tool_ids)
        source_summaries = []
        for source_id in context.deps.session_source_ids:
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
            selected_tools=selected_tools_context,
            source_summary="\n\n".join(source_summaries)
            if source_summaries
            else "Empty summary",
        )

    return agent
