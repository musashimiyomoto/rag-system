from pydantic_ai.models import Model, google, openai
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from enums import ProviderName
from exceptions import ProviderValidationError
from settings import ollama_settings


def get_model(
    provider_name: ProviderName, model_name: str, api_key: str
) -> tuple[Model, ModelSettings]:
    """Build model client by runtime provider configuration.

    Args:
        provider_name: The provider name.
        model_name: The model name.
        api_key: The API key.

    Returns:
        The model and settings.

    """
    if provider_name == ProviderName.GOOGLE:
        return (
            google.GoogleModel(
                model_name=model_name, provider=GoogleProvider(api_key=api_key)
            ),
            google.GoogleModelSettings(),
        )

    if provider_name == ProviderName.OPENAI:
        return (
            openai.OpenAIChatModel(
                model_name=model_name, provider=OpenAIProvider(api_key=api_key)
            ),
            openai.OpenAIChatModelSettings(),
        )

    if provider_name == ProviderName.OLLAMA:
        return (
            openai.OpenAIChatModel(
                model_name=model_name,
                provider=OllamaProvider(base_url=f"{ollama_settings.url}/v1"),
            ),
            openai.OpenAIChatModelSettings(),
        )

    raise ProviderValidationError(message=f"Unsupported provider: {provider_name}")
