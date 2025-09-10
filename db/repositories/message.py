from db.models import Message
from db.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self):
        super().__init__(model=Message)
