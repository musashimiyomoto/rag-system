import anthropic
import google.genai as google
import httpx
import openai

from constants import DEFAULT_TIMEOUT, GITHUB_MODELS_URL
from enums import ProviderName
from exceptions import ProviderUpstreamError
from schemas import ProviderModelResponse
from settings import ollama_settings


def _list_openai_models(api_key: str) -> list[ProviderModelResponse]:
    """List available OpenAI models.

    Args:
        api_key: Provider API key.

    Returns:
        Available OpenAI models as normalized response objects.

    Raises:
        ProviderUpstreamError: If the provider request fails.

    """
    try:
        with openai.Client(api_key=api_key) as client:
            return [
                ProviderModelResponse(name=model.id) for model in client.models.list()
            ]
    except Exception as error:
        raise ProviderUpstreamError(
            message=f"Failed to fetch OpenAI models: {error}"
        ) from error


def _list_google_models(api_key: str) -> list[ProviderModelResponse]:
    """List available Google models.

    Args:
        api_key: Provider API key.

    Returns:
        Available Google models as normalized response objects.

    Raises:
        ProviderUpstreamError: If the provider request fails.

    """
    try:
        with google.Client(api_key=api_key) as client:
            return [
                ProviderModelResponse(name=model.name)
                for model in client.models.list()
                if model.name is not None
            ]
    except Exception as error:
        raise ProviderUpstreamError(
            message=f"Failed to fetch Google models: {error}"
        ) from error


def _list_anthropic_models(api_key: str) -> list[ProviderModelResponse]:
    """List available Anthropic models.

    Args:
        api_key: Provider API key.

    Returns:
        Available Anthropic models as normalized response objects.

    Raises:
        ProviderUpstreamError: If the provider request fails.

    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        models = client.models.list()
        client.close()
        return [
            ProviderModelResponse(name=model.id)
            for model in models
            if isinstance(model.id, str)
        ]
    except Exception as error:
        raise ProviderUpstreamError(
            message=f"Failed to fetch Anthropic models: {error}"
        ) from error


def _list_github_models(api_key: str) -> list[ProviderModelResponse]:
    """List available GitHub-hosted models.

    Args:
        api_key: Provider API key.

    Returns:
        Available GitHub models as normalized response objects.

    Raises:
        ProviderUpstreamError: If the provider request fails.

    """
    try:
        response = httpx.get(url=GITHUB_MODELS_URL, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ProviderUpstreamError(
            message=f"Failed to fetch GitHub models: {error}"
        ) from error

    return [
        ProviderModelResponse(name=item["id"])
        for item in data
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]


def _list_ollama_models() -> list[ProviderModelResponse]:
    """List available Ollama models.

    Returns:
        Available Ollama models as normalized response objects.

    Raises:
        ProviderUpstreamError: If the provider request fails.

    """
    try:
        response = httpx.get(
            url=f"{ollama_settings.url}/api/tags", timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ProviderUpstreamError(
            message=f"Failed to fetch Ollama models: {error}"
        ) from error

    return [
        ProviderModelResponse(name=model["name"])
        for model in data.get("models", [])
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    ]


def list_provider_models(
    name: ProviderName, api_key: str
) -> list[ProviderModelResponse]:
    """List provider models.

    Args:
        name: The name parameter.
        api_key: The api_key parameter.

    Returns:
        List of provider models.

    """
    match name:
        case ProviderName.OPENAI:
            return _list_openai_models(api_key=api_key)
        case ProviderName.GOOGLE:
            return _list_google_models(api_key=api_key)
        case ProviderName.ANTHROPIC:
            return _list_anthropic_models(api_key=api_key)
        case ProviderName.GITHUB:
            return _list_github_models(api_key=api_key)
        case ProviderName.OLLAMA:
            return _list_ollama_models()
        case _:
            raise ProviderUpstreamError(message=f"Unsupported provider: {name}")
