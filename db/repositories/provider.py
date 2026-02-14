from db.models import Provider
from db.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    def __init__(self):
        super().__init__(model=Provider)
