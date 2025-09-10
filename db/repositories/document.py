from db.models import Document
from db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self):
        super().__init__(model=Document)
