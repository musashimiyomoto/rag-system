from enum import StrEnum


class Provider(StrEnum):
    GOOGLE = "google"
    GITHUB = "github"
    OPENAI = "openai"


class LLMName(StrEnum):
    # Google
    GEMINI_2_5_PRO = f"{Provider.GOOGLE.value}:gemini-2.5-pro"
    GEMINI_2_5_FLASH = f"{Provider.GOOGLE.value}:gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = f"{Provider.GOOGLE.value}:gemini-2.5-flash-lite"
    # GitHub
    GITHUB_XAI_GROK_3_MINI = f"{Provider.GITHUB.value}:xai/grok-3-mini"
    GITHUB_GPT_4_O = f"{Provider.GITHUB.value}:gpt-4o"
    GITHUB_GPT_4_O_MINI = f"{Provider.GITHUB.value}:gpt-4o-mini"
    # OpenAI
    OPENAI_GPT_5 = f"{Provider.OPENAI.value}:gpt-5"
    OPENAI_GPT_5_MINI = f"{Provider.OPENAI.value}:gpt-5-mini"
    OPENAI_GPT_5_NANO = f"{Provider.OPENAI.value}:gpt-5-nano"

    def decompose(self) -> tuple[Provider, str]:
        """Decompose the model into provider and llm name.

        Returns:
            The provider and model name.

        """
        provider, model_name = self.value.split(":")
        return Provider(provider), model_name
