from typing import TypedDict

from db.models import SourceDb
from enums import SourceType


class SourceProcessData(TypedDict):
    id: int
    name: str
    type: SourceType
    collection: str
    source_db: SourceDb | None
