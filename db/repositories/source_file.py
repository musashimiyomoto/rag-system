from db.models import SourceFile
from db.repositories.base import BaseRepository


class SourceFileRepository(BaseRepository[SourceFile]):
    def __init__(self):
        super().__init__(model=SourceFile)
