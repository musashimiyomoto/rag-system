from db.models import Session
from tests.factories.base import AsyncSQLAlchemyModelFactory


class SessionFactory(AsyncSQLAlchemyModelFactory):
    class Meta:
        model = Session
