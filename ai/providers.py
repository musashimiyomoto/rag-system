import google.genai as google
import openai

from enums import ProviderName
from exceptions import ProviderUpstreamError
from schemas import ProviderModelResponse


def list_provider_models(
    name: ProviderName, api_key: str
) -> list[ProviderModelResponse]:
    if name == ProviderName.OPENAI:
        return [
            ProviderModelResponse(name=model.id)
            for model in openai.Client(api_key=api_key).models.list()
        ]

    if name == ProviderName.GOOGLE:
        return [
            ProviderModelResponse(name=model.name)
            for model in google.Client(api_key=api_key).models.list()
            if model.name is not None
        ]

    raise ProviderUpstreamError(message=f"Unsupported provider: {name}")
