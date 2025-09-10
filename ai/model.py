from pydantic_ai.models import Model, google, openai
from pydantic_ai.providers.github import GitHubProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from enums import LLMName, Provider
from settings.core import core_settings


def get_model(llm: LLMName) -> tuple[Model, ModelSettings]:
    """Get a model by llm name.

    Args:
        llm: The llm name.

    Returns:
        The model and settings.

    """
    if (
        not core_settings.google_api_key
        and not core_settings.github_api_key
        and not core_settings.openai_api_key
    ):
        msg = "Google API key or GitHub API key or OpenAI API key are required"
        raise ValueError(msg)

    provider, model_name = llm.decompose()
    if provider == Provider.GOOGLE:
        return (
            google.GoogleModel(
                model_name=model_name,
                provider=GoogleProvider(api_key=core_settings.google_api_key),
            ),
            google.GoogleModelSettings(
                google_thinking_config={"include_thoughts": True}
            ),
        )
    if provider == Provider.GITHUB:
        return (
            openai.OpenAIChatModel(
                model_name=model_name,
                provider=GitHubProvider(api_key=core_settings.github_api_key),
            ),
            openai.OpenAIChatModelSettings(),
        )
    if provider == Provider.OPENAI:
        return (
            openai.OpenAIChatModel(
                model_name=model_name,
                provider=OpenAIProvider(api_key=core_settings.openai_api_key),
            ),
            openai.OpenAIChatModelSettings(),
        )

    msg = f"Provider {provider} not supported"
    raise ValueError(msg)
