from db.models import Source
from db.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    def __init__(self):
        super().__init__(model=Source)
