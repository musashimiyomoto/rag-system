from factory.declarations import LazyAttribute

from db.models import SessionSource
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class SessionSourceFactory(AsyncSQLAlchemyModelFactory):
    class Meta:
        model = SessionSource

    session_id = LazyAttribute(lambda obj: fake.pyint(min_value=1))
    source_id = LazyAttribute(lambda obj: fake.pyint(min_value=1))
