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
    POSTGRES = auto()
    CLICKHOUSE = auto()

    @classmethod
    def get_file_types(cls) -> set["SourceType"]:
        return {
            cls.PDF,
            cls.TXT,
            cls.MD,
            cls.DOCX,
            cls.RTF,
            cls.ODT,
            cls.EPUB,
            cls.HTML,
            cls.HTM,
            cls.PPTX,
            cls.XLSX,
            cls.EML,
        }

    @classmethod
    def get_db_types(cls) -> set["SourceType"]:
        return {cls.POSTGRES, cls.CLICKHOUSE}


class SourceStatus(StrEnum):
    CREATED = auto()
    PROCESSED = auto()
    COMPLETED = auto()
    FAILED = auto()
