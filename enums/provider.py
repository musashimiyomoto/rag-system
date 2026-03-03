from enum import StrEnum, auto


class ProviderName(StrEnum):
    ANTHROPIC = auto()
    GITHUB = auto()
    GOOGLE = auto()
    OPENAI = auto()
    OLLAMA = auto()
