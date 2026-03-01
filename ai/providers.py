import google.genai as google
import httpx
import openai

from enums import ProviderName
from exceptions import ProviderUpstreamError
from schemas import ProviderModelResponse
from settings import ollama_settings


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
    if name == ProviderName.OPENAI:
        with openai.Client(api_key=api_key) as client:
            return [
                ProviderModelResponse(name=model.id) for model in client.models.list()
            ]

    if name == ProviderName.GOOGLE:
        with google.Client(api_key=api_key) as client:
            return [
                ProviderModelResponse(name=model.name)
                for model in client.models.list()
                if model.name is not None
            ]

    if name == ProviderName.OLLAMA:
        try:
            response = httpx.get(
                url=f"{ollama_settings.url}/api/tags",
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUpstreamError(
                message=f"Failed to fetch Ollama models: {error}"
            ) from error

        models = data.get("models", []) if isinstance(data, dict) else []
        return [
            ProviderModelResponse(name=model["name"])
            for model in models
            if isinstance(model, dict) and isinstance(model.get("name"), str)
        ]

    raise ProviderUpstreamError(message=f"Unsupported provider: {name}")
