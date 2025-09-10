from factory.declarations import LazyAttribute

from db.models import Document
from enums import DocumentStatus, DocumentType
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class DocumentFactory(AsyncSQLAlchemyModelFactory):
    class Meta:  # type: ignore
        model = Document

    name = LazyAttribute(lambda obj: fake.name())
    type = DocumentType.PDF
    status = DocumentStatus.CREATED
    collection = LazyAttribute(lambda obj: fake.uuid4())
    summary = LazyAttribute(lambda obj: fake.text())
