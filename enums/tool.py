from enum import StrEnum, auto


class ToolId(StrEnum):
    RETRIEVE = auto()
    WEB_SEARCH = auto()


class ToolRuntimeRequirement(StrEnum):
    SESSION = auto()
    SOURCES = auto()
    RETRIEVE_CONFIG = auto()
