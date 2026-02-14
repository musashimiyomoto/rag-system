from db.models import SessionSource
from db.repositories.base import BaseRepository


class SessionSourceRepository(BaseRepository[SessionSource]):
    def __init__(self):
        super().__init__(model=SessionSource)
