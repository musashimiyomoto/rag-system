from enum import StrEnum, auto


class SourceType(StrEnum):
    PDF = auto()
    TXT = auto()
    MD = auto()
    DOCX = auto()
    RTF = auto()
    ODT = auto()
    EPUB = auto()
    HTML = auto()
    HTM = auto()
    PPTX = auto()
    XLSX = auto()
    EML = auto()


class SourceStatus(StrEnum):
    CREATED = auto()
    PROCESSED = auto()
    COMPLETED = auto()
    FAILED = auto()
