from datetime import datetime, timezone

from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from ai.dependencies import AgentDeps
from ai.model import get_model
from ai.prompts import SYSTEM_PROMPT
from ai.tools import TOOL_REGISTRY, get_tools
from constants import WEEKEND_START_WEEKDAY
from db.repositories import ProviderRepository, SourceRepository
from enums import ToolId
from exceptions import ProviderConflictError, ProviderNotFoundError
from utils import decrypt


def _render_selected_tools_context(tool_ids: list[ToolId]) -> str:
    """Render selected tools for the system prompt.

    Args:
        tool_ids: Tool IDs selected for this run.

    Returns:
        Human-readable list of selected tools for prompt context.

    """
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


def _render_runtime_context(
    provider_id: int,
    model_name: str,
    tool_ids: list[ToolId],
    session_id: int,
    session_source_ids: list[int],
) -> str:
    """Render runtime metadata for prompt context in UTC.

    Args:
        provider_id: Selected provider ID.
        model_name: Selected model name.
        tool_ids: Tool IDs selected for this run.
        session_id: Active session ID.
        session_source_ids: Source IDs attached to the active session.

    Returns:
        Newline-separated runtime context block for the system prompt.

    """
    now = datetime.now(timezone.utc)
    iso_datetime = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    iso_year, iso_week, _ = now.isocalendar()
    is_weekend = now.weekday() >= WEEKEND_START_WEEKDAY
    selected_tool_ids = ", ".join(str(tool_id) for tool_id in tool_ids) or "none"
    session_sources = ", ".join(str(source_id) for source_id in session_source_ids)
    session_source_ids_text = session_sources or "none"

    return "\n".join(
        [
            f"current_datetime_utc: {iso_datetime}",
            f"current_date_utc: {now:%Y-%m-%d}",
            f"current_time_utc: {now:%H:%M:%S}",
            f"current_weekday_utc: {now:%A}",
            f"current_unix_timestamp: {int(now.timestamp())}",
            "timezone: UTC",
            f"year: {now.year}",
            f"month: {now.month}",
            f"day: {now.day}",
            f"iso_week: {iso_year}-W{iso_week:02d}",
            f"day_of_year: {now.timetuple().tm_yday}",
            f"is_weekend_utc: {str(is_weekend).lower()}",
            f"session_id: {session_id}",
            f"provider_id: {provider_id}",
            f"model_name: {model_name}",
            f"selected_tool_ids: {selected_tool_ids}",
            f"selected_tools_count: {len(tool_ids)}",
            f"session_source_count: {len(session_source_ids)}",
            f"session_source_ids: {session_source_ids_text}",
        ]
    )


async def _render_summary_context(session: AsyncSession, source_ids: list[int]) -> str:
    """Render source summaries for the current chat session.

    Args:
        session: The database session.
        source_ids: Source IDs attached to the chat session.

    Returns:
        Concatenated source summaries or a fallback text when empty.

    """
    source_summaries = []
    for source_id in source_ids:
        source = await SourceRepository().get_by(session=session, id=source_id)
        if not source or not source.summary:
            continue

        source_summaries.append(f"[source:{source.id}] {source.name}\n{source.summary}")

    return "\n\n".join(source_summaries) if source_summaries else "Empty summary"


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
        return SYSTEM_PROMPT.format(
            selected_tools=_render_selected_tools_context(tool_ids=tool_ids),
            runtime_context=_render_runtime_context(
                provider_id=provider_id,
                model_name=model_name,
                tool_ids=tool_ids,
                session_id=context.deps.session_id,
                session_source_ids=context.deps.session_source_ids,
            ),
            source_summary=await _render_summary_context(
                session=context.deps.session, source_ids=context.deps.session_source_ids
            ),
        )

    return agent
