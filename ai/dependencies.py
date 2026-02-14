from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class Dependencies:
    session: AsyncSession
    source_id: int
    n_results: int = 5
