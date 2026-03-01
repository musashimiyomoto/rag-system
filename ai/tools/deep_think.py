from pydantic_ai import RunContext

from ai.dependencies import AgentDeps


async def deep_think(
    context: RunContext[AgentDeps], task: str, constraints: str | None = None
) -> str:
    """Produce a structured reasoning trace for the current task.

    Args:
        context: The call context.
        task: The task to reason about.
        constraints: Optional constraints and priorities.

    Returns:
        A concise structured analysis.

    """
    normalized_task = task.strip()
    if len(normalized_task) == 0:
        return "Task is empty. Provide a concrete task to analyze."

    constraints_text = constraints.strip() if constraints else "No extra constraints."
    return (
        "Goal:\n"
        f"- {normalized_task}\n\n"
        "Reasoning:\n"
        "- Clarify expected outcome and acceptance criteria.\n"
        "- Identify key assumptions, dependencies, and risks.\n"
        "- Decompose work into minimal safe implementation steps.\n"
        "- Validate with focused tests and edge-case checks.\n\n"
        "Constraints:\n"
        f"- {constraints_text}\n\n"
        "Execution Plan:\n"
        "- Implement smallest working change first.\n"
        "- Verify behavior incrementally.\n"
        "- Refine only if tests or constraints require it."
    )
