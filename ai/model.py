from pydantic_ai.models import Model, anthropic, google, openai
from pydantic_ai.providers.anthropic import AnthropicProvider
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
    match provider_name:
        case ProviderName.GOOGLE:
            return (
                google.GoogleModel(
                    model_name=model_name, provider=GoogleProvider(api_key=api_key)
                ),
                google.GoogleModelSettings(),
            )
        case ProviderName.OPENAI:
            return (
                openai.OpenAIChatModel(
                    model_name=model_name, provider=OpenAIProvider(api_key=api_key)
                ),
                openai.OpenAIChatModelSettings(),
            )
        case ProviderName.ANTHROPIC:
            return (
                anthropic.AnthropicModel(
                    model_name=model_name, provider=AnthropicProvider(api_key=api_key)
                ),
                anthropic.AnthropicModelSettings(),
            )
        case ProviderName.GITHUB:
            return (
                openai.OpenAIChatModel(
                    model_name=model_name, provider=OpenAIProvider(api_key=api_key)
                ),
                openai.OpenAIChatModelSettings(),
            )
        case ProviderName.OLLAMA:
            return (
                openai.OpenAIChatModel(
                    model_name=model_name,
                    provider=OllamaProvider(base_url=f"{ollama_settings.url}/v1"),
                ),
                openai.OpenAIChatModelSettings(),
            )
        case _:
            raise ProviderValidationError(
                message=f"Unsupported provider: {provider_name}"
            )
