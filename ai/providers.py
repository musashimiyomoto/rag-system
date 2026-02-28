import google.genai as google
import openai

from enums import ProviderName
from exceptions import ProviderUpstreamError
from schemas import ProviderModelResponse


def list_provider_models(
    name: ProviderName, api_key: str
) -> list[ProviderModelResponse]:
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

    raise ProviderUpstreamError(message=f"Unsupported provider: {name}")
