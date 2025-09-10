from factory.declarations import LazyAttribute

from db.models import Message
from enums import Role
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class MessageFactory(AsyncSQLAlchemyModelFactory[Message]):
    class Meta:  # type: ignore
        model = Message

    session_id = LazyAttribute(lambda obj: fake.pyint(min_value=1))

    role = Role.USER
    content = LazyAttribute(lambda obj: fake.text())
    thinking = LazyAttribute(lambda obj: fake.text())
    timestamp = LazyAttribute(lambda obj: fake.date_time())
