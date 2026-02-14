from enum import StrEnum, auto


class ProviderName(StrEnum):
    GOOGLE = auto()
    OPENAI = auto()


class ProviderBaseUrl(StrEnum):
    GOOGLE = "https://generativelanguage.googleapis.com/v1beta"
    OPENAI = "https://api.openai.com/v1"
