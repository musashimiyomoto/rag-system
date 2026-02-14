import asyncio

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters

from ai.model import get_model
from ai.prompts.summary import SUMMARY_PROMPT
from constants import RATE_LIMIT_DELAY
from enums import ProviderName
from utils import decrypt


async def summarize(
    texts: list[str],
    provider_name: ProviderName,
    model_name: str,
    api_key_encrypted: str,
) -> str:
    """Summarize source chunks using default summary provider.

    Args:
        texts: The list of source chunks to summarize.
        provider_name: The provider name.
        model_name: The model name.
        api_key_encrypted: The encrypted API key.

    Returns:
        The final source summary.

    """
    model, _ = get_model(
        provider_name=provider_name,
        model_name=model_name,
        api_key=decrypt(encrypted_data=api_key_encrypted),
    )

    messages: list[ModelMessage] = [
        ModelRequest(parts=[SystemPromptPart(content=SUMMARY_PROMPT)])
    ]
    messages.extend(
        [ModelRequest(parts=[UserPromptPart(content=text)]) for text in texts]
    )

    try:
        response = await model.request(
            messages=messages,
            model_settings=None,
            model_request_parameters=ModelRequestParameters(),
        )
    except Exception:
        await asyncio.sleep(delay=RATE_LIMIT_DELAY)
        response = await model.request(
            messages=messages,
            model_settings=None,
            model_request_parameters=ModelRequestParameters(),
        )

    return "\n\n".join(
        [part.content for part in response.parts if isinstance(part, TextPart)]
    )
