from enum import StrEnum, auto


class SourceType(StrEnum):
    PDF = auto()
    TXT = auto()


class SourceStatus(StrEnum):
    CREATED = auto()
    PROCESSED = auto()
    COMPLETED = auto()
    FAILED = auto()
