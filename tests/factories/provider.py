from db.models import Provider
from enums import ProviderName
from tests.factories.base import AsyncSQLAlchemyModelFactory, fake


class ProviderFactory(AsyncSQLAlchemyModelFactory):
    class Meta:
        model = Provider

    name = ProviderName.OPENAI
    api_key_encrypted = fake.sha256()
    is_active = True
