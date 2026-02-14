from factory.declarations import LazyAttribute

from db.models import Session
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class SessionFactory(AsyncSQLAlchemyModelFactory[Session]):
    class Meta:
        model = Session

    source_id = LazyAttribute(lambda obj: fake.pyint(min_value=1))
