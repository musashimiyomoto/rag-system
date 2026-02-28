from db.models import SourceDb
from db.repositories.base import BaseRepository


class SourceDbRepository(BaseRepository[SourceDb]):
    def __init__(self):
        super().__init__(model=SourceDb)
