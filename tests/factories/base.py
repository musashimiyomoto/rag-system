from typing import TypeVar, cast

from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

fake = Faker("en_US")

ModelT = TypeVar("ModelT")


class AsyncSQLAlchemyModelFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs: object) -> ModelT:
        instance = cls.build(**kwargs)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return cast("ModelT", instance)
