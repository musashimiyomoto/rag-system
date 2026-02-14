from factory.declarations import LazyAttribute

from db.models import SourceFile
from tests.factories.base import AsyncSQLAlchemyModelFactory


class SourceFileFactory(AsyncSQLAlchemyModelFactory):
    class Meta:
        model = SourceFile

    source_id = 1
    content = LazyAttribute(lambda _: b"Sample source content")
