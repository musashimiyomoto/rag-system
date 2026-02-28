from factory.declarations import LazyAttribute

from db.models import SourceDb
from enums import SourceType
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class SourceDbFactory(AsyncSQLAlchemyModelFactory):
    class Meta:
        model = SourceDb

    source_id = LazyAttribute(lambda obj: fake.pyint(min_value=1))
    db_type = SourceType.POSTGRES
    connection_encrypted = LazyAttribute(lambda obj: fake.sha256())
    schema_name = "public"
    table_name = LazyAttribute(lambda obj: fake.slug())
    id_field = "id"
    search_field = "content"
    filter_fields = ["category"]
