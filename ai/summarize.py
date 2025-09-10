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
from enums import LLMName
from settings.core import core_settings


async def summarize(text: str) -> str:
    """Summarize the document.

    Args:
        text: The text to summarize.

    Returns:
        The summarized document.

    Raises:
        ClientError: If the client error occurs.

    """
    if core_settings.google_api_key:
        model, _ = get_model(llm=LLMName.GEMINI_2_5_FLASH_LITE)
    elif core_settings.github_api_key:
        model, _ = get_model(llm=LLMName.GITHUB_GPT_4_O_MINI)
    elif core_settings.openai_api_key:
        model, _ = get_model(llm=LLMName.OPENAI_GPT_5_NANO)
    else:
        msg = "Google API key or GitHub API key or OpenAI API key is required"
        raise ValueError(msg)

    messages: list[ModelMessage] = [
        ModelRequest(parts=[SystemPromptPart(content=SUMMARY_PROMPT)]),
        ModelRequest(parts=[UserPromptPart(content=text)]),
    ]

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
