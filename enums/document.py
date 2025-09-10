from enum import StrEnum, auto


class DocumentType(StrEnum):
    PDF = auto()
    TXT = auto()


class DocumentStatus(StrEnum):
    CREATED = auto()
    PROCESSED = auto()
    COMPLETED = auto()
    FAILED = auto()
