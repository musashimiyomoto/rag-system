from db.models import Session
from db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self):
        super().__init__(model=Session)
