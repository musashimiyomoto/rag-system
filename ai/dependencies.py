from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class Dependencies:
    session: AsyncSession
    source_ids: list[int]
    n_results: int = 8
    n_sources: int = 3
