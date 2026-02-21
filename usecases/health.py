import asyncio
from http import HTTPStatus

import httpx
from sqlalchemy import text

from db.sessions import async_session
from settings import prefect_settings, qdrant_settings


class HealthUsecase:
    async def check_postgres(self) -> bool:
        """Check postgres connectivity.

        Returns:
            True if postgres is healthy, False otherwise.

        """
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    async def check_qdrant(self) -> bool:
        """Check Qdrant connectivity.

        Returns:
            True if qdrant is healthy, False otherwise.

        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{qdrant_settings.url}/healthz",
                    timeout=5.0,
                )
                return response.status_code == HTTPStatus.OK
        except Exception:
            return False

    async def check_prefect(self) -> bool:
        """Check Prefect server connectivity.

        Returns:
            True if prefect is healthy, False otherwise.

        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{prefect_settings.url}/api/health",
                    timeout=5.0,
                )
                return response.status_code == HTTPStatus.OK
        except Exception:
            return False

    async def health(self) -> dict[str, bool]:
        """Check all services concurrently.

        Returns:
            Dictionary of service names and their health status.

        """
        tasks = [
            ("postgres", self.check_postgres()),
            ("qdrant", self.check_qdrant()),
            ("prefect", self.check_prefect()),
        ]

        results = await asyncio.gather(
            *[task[1] for task in tasks], return_exceptions=True
        )

        service_checks = {}
        for service_name, result in zip(
            [task[0] for task in tasks], results, strict=True
        ):
            if isinstance(result, Exception):
                service_checks[service_name] = False
            else:
                service_checks[service_name] = result

        return service_checks
