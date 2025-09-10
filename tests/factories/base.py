from typing import Generic, TypeVar

import factory
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

fake = Faker("en_US")

TestModel = TypeVar("TestModel", bound=object)


class AsyncSQLAlchemyModelFactory(
    factory.alchemy.SQLAlchemyModelFactory, Generic[TestModel]
):
    class Meta:  # type: ignore
        abstract = True
        sqlalchemy_session_persistence = "commit"

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs) -> TestModel:
        instance = cls.build(**kwargs)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance
