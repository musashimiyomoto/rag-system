from factory.declarations import LazyAttribute

from db.models import Source
from enums import SourceStatus, SourceType
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class SourceFactory(AsyncSQLAlchemyModelFactory):
    class Meta:
        model = Source

    name = LazyAttribute(lambda obj: fake.name())
    type = SourceType.PDF
    status = SourceStatus.CREATED
    collection = LazyAttribute(lambda obj: fake.uuid4())
    summary = LazyAttribute(lambda obj: fake.text())
